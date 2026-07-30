/// Hold-to-record, the way every messenger does it.
///
/// The gestures are not decoration. Holding a button to record means every
/// recording starts with a press that might have been a mis-tap, so there has
/// to be a way out that is not "send it anyway": slide left to cancel, slide up
/// to lock and keep both hands free. A voice feature without those is one that
/// punishes a slip of the thumb by broadcasting it.
library;

import 'dart:async';
import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';

/// A finished recording, ready to send.
class VoiceRecording {
  final String path;
  final int durationMs;

  /// Amplitude buckets 0..100 sampled while recording, so the bubble can draw
  /// a waveform without anyone decoding the audio.
  final List<int> waveform;

  const VoiceRecording({
    required this.path,
    required this.durationMs,
    required this.waveform,
  });
}

/// Ceiling matching the server's. Enforced here too so a long recording is
/// stopped while the person can still see why, rather than rejected after the
/// upload.
const kMaxVoiceDuration = Duration(minutes: 2);

/// How far left the finger must travel before a release cancels.
const _kCancelThreshold = 90.0;

/// How far up before the recording locks and the finger is free.
const _kLockThreshold = 70.0;

/// Waveform buckets, matching the server's cap.
const _kWaveformBuckets = 48;

enum _RecorderPhase { idle, recording, locked }

class VoiceRecorderBar extends StatefulWidget {
  /// Called with the finished recording. Never called for a cancel.
  final void Function(VoiceRecording) onComplete;

  /// Whether a recording is in progress, so the composer can hide its input.
  final void Function(bool active) onActiveChanged;

  /// Injectable so tests do not need a microphone.
  final AudioRecorder Function()? recorderFactory;

  /// Where the recording is written. Injectable for the same reason as
  /// [recorderFactory]: the default goes through path_provider, which is a
  /// platform channel with no implementation under `flutter test` — an
  /// unmocked call there never returns, so the test hangs instead of failing.
  final Future<Directory> Function()? directoryProvider;

  const VoiceRecorderBar({
    super.key,
    required this.onComplete,
    required this.onActiveChanged,
    this.recorderFactory,
    this.directoryProvider,
  });

  @override
  State<VoiceRecorderBar> createState() => VoiceRecorderBarState();
}

class VoiceRecorderBarState extends State<VoiceRecorderBar> {
  AudioRecorder? _recorder;
  Timer? _ticker;
  StreamSubscription<Amplitude>? _amplitudes;

  _RecorderPhase _phase = _RecorderPhase.idle;

  /// Guards against finishing twice. Both endings are async, and the ticker
  /// keeps firing across the first await — without this, hitting the ceiling
  /// queues a second `_finish` that sends the same recording again after the
  /// first has already cleared the path.
  bool _finishing = false;

  Duration _elapsed = Duration.zero;
  double _dragX = 0;
  double _dragY = 0;
  final List<int> _waveform = [];
  String? _path;

  bool get isActive => _phase != _RecorderPhase.idle;
  bool get _willCancel => _dragX <= -_kCancelThreshold;

  @override
  void dispose() {
    _ticker?.cancel();
    _amplitudes?.cancel();
    _recorder?.dispose();
    super.dispose();
  }

  Future<void> start() async {
    final recorder = (widget.recorderFactory ?? AudioRecorder.new)();
    if (!await recorder.hasPermission()) {
      await recorder.dispose();
      if (mounted) _denied();
      return;
    }

    final dir = await (widget.directoryProvider ?? getTemporaryDirectory)();
    final path =
        '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}.m4a';

    // AAC in an MP4 container is what both platforms produce natively and what
    // the server accepts — encoding here means no ffmpeg on a worker. 32kbps
    // mono is transparent for speech and keeps two minutes under half a
    // megabyte.
    await recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.aacLc,
        bitRate: 32000,
        numChannels: 1,
        sampleRate: 22050,
      ),
      path: path,
    );

    _recorder = recorder;
    _path = path;
    _waveform.clear();
    HapticFeedback.mediumImpact();

    _ticker = Timer.periodic(const Duration(milliseconds: 100), (timer) {
      if (!mounted) return;
      setState(() => _elapsed += const Duration(milliseconds: 100));
      if (_elapsed >= kMaxVoiceDuration && !_finishing) {
        // Cancelled here rather than relying on the teardown inside _finish:
        // that happens after an await, and the ticker would go on firing in
        // the meantime.
        timer.cancel();
        _finish();
      }
    });

    _amplitudes = recorder
        .onAmplitudeChanged(const Duration(milliseconds: 120))
        .listen((amplitude) {
          if (!mounted) return;
          setState(() => _waveform.add(_bucket(amplitude.current)));
        });

    setState(() {
      _phase = _RecorderPhase.recording;
      _elapsed = Duration.zero;
      _dragX = 0;
      _dragY = 0;
    });
    widget.onActiveChanged(true);
  }

  /// dBFS (roughly -60..0) to a 0..100 bar height.
  int _bucket(double dbfs) {
    if (dbfs.isNaN || dbfs.isInfinite) return 0;
    final normalised = ((dbfs + 60) / 60).clamp(0.0, 1.0);
    return (normalised * 100).round();
  }

  /// [offsetFromOrigin] is cumulative, as the gesture reports it — tracking
  /// deltas here would drift, and a cancel that needs a slightly different
  /// slide each time is worse than no cancel at all.
  void onDrag(Offset offsetFromOrigin) {
    if (_phase != _RecorderPhase.recording) return;
    setState(() {
      _dragX = math.min(0, offsetFromOrigin.dx);
      _dragY = math.min(0, offsetFromOrigin.dy);
    });
    if (-_dragY >= _kLockThreshold) {
      HapticFeedback.selectionClick();
      setState(() {
        _phase = _RecorderPhase.locked;
        _dragX = 0;
      });
    }
  }

  /// Finger lifted. Cancels if it travelled far enough left, otherwise sends.
  Future<void> onRelease() async {
    if (_phase != _RecorderPhase.recording) return; // locked: the button decides
    if (_willCancel) {
      await cancel();
    } else {
      await _finish();
    }
  }

  Future<void> cancel() async {
    if (_finishing) return;
    _finishing = true;
    HapticFeedback.heavyImpact();
    final path = _path;
    await _stopRecorder();
    // The file goes with the gesture. A cancelled recording that survives on
    // disk is exactly the thing the gesture exists to prevent.
    if (path != null) {
      try {
        // Sync on purpose: this is a handful of kilobytes in a temp directory,
        // and the async form hands control back mid-teardown, which leaves the
        // bar on screen for a frame after the person has already let go.
        final file = File(path);
        if (file.existsSync()) file.deleteSync();
      } catch (_) {
        // Nothing useful to do; the OS clears its own temp directory.
      }
    }
    _reset();
  }

  Future<void> _finish() async {
    if (_finishing) return;
    _finishing = true;
    final path = _path;
    final elapsed = _elapsed;
    final waveform = _downsample(_waveform);
    await _stopRecorder();

    // Under a second is a mis-press, not a message.
    if (path != null && elapsed.inMilliseconds >= 1000) {
      widget.onComplete(
        VoiceRecording(
          path: path,
          durationMs: elapsed.inMilliseconds,
          waveform: waveform,
        ),
      );
    } else if (path != null) {
      try {
        final file = File(path);
        if (file.existsSync()) file.deleteSync();
      } catch (_) {}
    }
    _reset();
  }

  Future<void> _stopRecorder() async {
    _ticker?.cancel();

    // Only `stop` is awaited, because only `stop` produces something we need:
    // it is what flushes the encoder and leaves a complete file on disk.
    // Cancelling the amplitude subscription and disposing the recorder are
    // teardown, and nothing downstream reads their result — making the
    // person's message wait on the microphone being released would add
    // latency to the one moment that should feel immediate.
    unawaited(_amplitudes?.cancel());
    _amplitudes = null;

    try {
      await _recorder?.stop();
    } catch (_) {
      // Already stopped, or the platform lost the session. Either way the
      // teardown below still has to run.
    }
    unawaited(_recorder?.dispose());
    _recorder = null;
  }

  void _reset() {
    _finishing = false;
    if (!mounted) return;
    setState(() {
      _phase = _RecorderPhase.idle;
      _elapsed = Duration.zero;
      _dragX = 0;
      _dragY = 0;
      _path = null;
      _waveform.clear();
    });
    widget.onActiveChanged(false);
  }

  /// Squeeze however many samples were taken into a fixed number of bars, so a
  /// six-second note and a two-minute one draw the same shape.
  List<int> _downsample(List<int> samples) {
    if (samples.length <= _kWaveformBuckets) return List.of(samples);
    final step = samples.length / _kWaveformBuckets;
    return List.generate(_kWaveformBuckets, (i) {
      final start = (i * step).floor();
      final end = math.min(samples.length, ((i + 1) * step).ceil());
      final slice = samples.sublist(start, end);
      return slice.reduce(math.max);
    });
  }

  void _denied() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Bliss needs microphone access to record a voice note.'),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_phase == _RecorderPhase.idle) return const SizedBox.shrink();

    final cancelling = _willCancel;
    return Container(
      key: const Key('voice_recorder_bar'),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.md,
      ),
      child: Row(
        children: [
          _PulsingDot(cancelling: cancelling),
          const SizedBox(width: AppSpacing.md),
          Text(
            _clock(_elapsed),
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontFeatures: const [FontFeature.tabularFigures()],
              color: cancelling ? AppColors.error : AppColors.softCharcoal,
            ),
          ),
          const SizedBox(width: AppSpacing.lg),
          Expanded(
            child: _phase == _RecorderPhase.locked
                ? Text(
                    'Recording — tap to send',
                    style: Theme.of(context).textTheme.bodySmall,
                  )
                : Transform.translate(
                    offset: Offset(_dragX.clamp(-_kCancelThreshold, 0), 0),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.chevron_left_rounded,
                          size: 18,
                          color: cancelling
                              ? AppColors.error
                              : AppColors.softCharcoal.withValues(alpha: 0.5),
                        ),
                        Text(
                          cancelling ? 'Release to cancel' : 'Slide to cancel',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: cancelling
                                ? AppColors.error
                                : AppColors.softCharcoal.withValues(alpha: 0.5),
                          ),
                        ),
                      ],
                    ),
                  ),
          ),
          if (_phase == _RecorderPhase.locked) ...[
            IconButton(
              key: const Key('voice_cancel'),
              onPressed: cancel,
              icon: const Icon(Icons.delete_outline_rounded),
              color: AppColors.error,
              tooltip: 'Discard',
            ),
            IconButton(
              key: const Key('voice_stop'),
              onPressed: _finish,
              icon: const Icon(Icons.send_rounded),
              color: AppColors.warmCoral,
              tooltip: 'Send',
            ),
          ] else
            Icon(
              Icons.lock_outline_rounded,
              size: 18,
              color: AppColors.softCharcoal.withValues(
                alpha: 0.3 + (-_dragY / _kLockThreshold).clamp(0.0, 0.7),
              ),
            ),
        ],
      ),
    );
  }

  String _clock(Duration d) {
    final seconds = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '${d.inMinutes}:$seconds';
  }
}

class _PulsingDot extends StatefulWidget {
  final bool cancelling;

  const _PulsingDot({required this.cancelling});

  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _controller.drive(Tween(begin: 0.35, end: 1)),
      child: Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(
          color: widget.cancelling ? AppColors.softCharcoal : AppColors.error,
          shape: BoxShape.circle,
        ),
      ),
    );
  }
}
