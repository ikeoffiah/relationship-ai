/// Photo and voice-note bubbles for the couple's thread.
///
/// Both render from a local file: an optimistic bubble from the file that is
/// still uploading, a received one from [MediaCache] once the proxy has
/// decrypted it. Neither ever points at the storage vendor — it holds
/// ciphertext, and only the server can undo that.
library;

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/features/couple_chat/media_cache.dart';
import 'package:mobile/features/couple_chat/models/couple_message.dart';
import 'package:mobile/features/couple_chat/models/message_media.dart';

/// Resolves a media path to a local file, showing [placeholder] until it lands.
///
/// One widget rather than a FutureBuilder at each call site, because every
/// media surface — bubble, thumbnail, full-screen viewer — needs the same
/// three states and the same failure behaviour.
class _LocalFile extends StatefulWidget {
  final String? localPath;
  final String? remotePath;
  final Widget Function(BuildContext, File) builder;
  final Widget placeholder;

  const _LocalFile({
    required this.localPath,
    required this.remotePath,
    required this.builder,
    required this.placeholder,
  });

  @override
  State<_LocalFile> createState() => _LocalFileState();
}

class _LocalFileState extends State<_LocalFile> {
  Future<File>? _future;

  @override
  void initState() {
    super.initState();
    _resolve();
  }

  @override
  void didUpdateWidget(_LocalFile old) {
    super.didUpdateWidget(old);
    if (old.remotePath != widget.remotePath || old.localPath != widget.localPath) {
      _resolve();
    }
  }

  void _resolve() {
    final local = widget.localPath;
    if (local != null) {
      _future = Future.value(File(local));
    } else if (widget.remotePath != null) {
      _future = MediaCache.instance.file(widget.remotePath!);
    } else {
      _future = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final future = _future;
    if (future == null) return widget.placeholder;
    return FutureBuilder<File>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.hasData) return widget.builder(context, snapshot.data!);
        if (snapshot.hasError) return const _Unavailable();
        return widget.placeholder;
      },
    );
  }
}

/// What a bubble shows when the bytes are gone — destroyed by a delete, or
/// blocked before delivery. Deliberately quiet: nothing here is an error the
/// reader can act on.
class _Unavailable extends StatelessWidget {
  const _Unavailable();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      alignment: Alignment.center,
      color: AppColors.softCharcoal.withValues(alpha: 0.05),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.image_not_supported_outlined,
            size: 18,
            color: AppColors.softCharcoal.withValues(alpha: 0.4),
          ),
          const SizedBox(width: AppSpacing.sm),
          Text(
            'Unavailable',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: AppColors.softCharcoal.withValues(alpha: 0.5),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Photos ──────────────────────────────────────────────────────────────────

class ImageBubble extends StatelessWidget {
  final CoupleMessage message;
  final VoidCallback? onRetry;

  const ImageBubble({super.key, required this.message, this.onRetry});

  @override
  Widget build(BuildContext context) {
    final media = message.media;
    if (media == null) return const _Unavailable();

    final image = ClipRRect(
      borderRadius: BorderRadius.circular(AppRadii.md),
      child: AspectRatio(
        aspectRatio: media.aspectRatio,
        child: _LocalFile(
          localPath: media.localPath,
          // The thumbnail in the thread, never the full image: a scroll past
          // twenty photos should not pull twenty full-size files.
          remotePath: media.localPath == null ? media.thumbUrl ?? media.url : null,
          placeholder: Container(color: AppColors.softCharcoal.withValues(alpha: 0.06)),
          builder: (_, file) => Image.file(file, fit: BoxFit.cover),
        ),
      ),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Stack(
          alignment: Alignment.center,
          children: [
            // Only openable once it is really on the server — tapping into a
            // full-screen view of a file that is still uploading would have
            // nothing to show.
            if (media.isLocal)
              image
            else
              GestureDetector(
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    fullscreenDialog: true,
                    builder: (_) => ImageViewer(media: media),
                  ),
                ),
                child: Hero(tag: 'media-${media.id}', child: image),
              ),
            if (message.isPending) _UploadRing(progress: message.uploadProgress ?? 0),
            if (message.failed && onRetry != null) _RetryOverlay(onRetry: onRetry!),
          ],
        ),
        if (message.body.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(message.body, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ],
    );
  }
}

/// Determinate ring over a photo that is still going up.
class _UploadRing extends StatelessWidget {
  final double progress;

  const _UploadRing({required this.progress});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.35),
        borderRadius: BorderRadius.circular(AppRadii.md),
      ),
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: SizedBox(
        width: 44,
        height: 44,
        child: CircularProgressIndicator(
          // Indeterminate until the first byte moves, so a stalled connection
          // does not sit at a confident 0%.
          value: progress > 0 ? progress : null,
          strokeWidth: 3,
          backgroundColor: Colors.white24,
          valueColor: const AlwaysStoppedAnimation(Colors.white),
        ),
      ),
    );
  }
}

class _RetryOverlay extends StatelessWidget {
  final VoidCallback onRetry;

  const _RetryOverlay({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: Material(
        color: Colors.black.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(AppRadii.md),
        child: InkWell(
          onTap: onRetry,
          child: const Center(
            child: Icon(Icons.refresh_rounded, color: Colors.white, size: 32),
          ),
        ),
      ),
    );
  }
}

/// Full-screen photo: pinch to zoom, swipe down to dismiss.
class ImageViewer extends StatefulWidget {
  final MessageMedia media;

  const ImageViewer({super.key, required this.media});

  @override
  State<ImageViewer> createState() => _ImageViewerState();
}

class _ImageViewerState extends State<ImageViewer> {
  double _dragOffset = 0;

  /// Watched so panning can be turned off until the photo is actually zoomed.
  ///
  /// InteractiveViewer claims the pan gesture whenever `panEnabled` is true,
  /// even at scale 1 where there is nowhere to pan to — which swallowed the
  /// swipe-down-to-dismiss entirely. Enabling pan only once zoomed gives both
  /// gestures the moment they are each useful.
  final _transform = TransformationController();
  bool _zoomed = false;

  @override
  void initState() {
    super.initState();
    _transform.addListener(_onTransform);
  }

  @override
  void dispose() {
    _transform.removeListener(_onTransform);
    _transform.dispose();
    super.dispose();
  }

  void _onTransform() {
    final zoomed = _transform.value.getMaxScaleOnAxis() > 1.01;
    if (zoomed != _zoomed) setState(() => _zoomed = zoomed);
  }

  @override
  Widget build(BuildContext context) {
    // Fades out as the sheet is dragged away, so the gesture feels like it is
    // moving the photo rather than triggering a transition.
    final opacity = (1 - (_dragOffset.abs() / 400)).clamp(0.0, 1.0);

    return Scaffold(
      backgroundColor: Colors.black.withValues(alpha: opacity),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      extendBodyBehindAppBar: true,
      // The drag is driven from InteractiveViewer's own callbacks rather than
      // an enclosing GestureDetector. Its scale recogniser claims
      // single-pointer drags even with `panEnabled: false`, so a competing
      // vertical-drag detector simply never fires and swipe-to-dismiss does
      // nothing at all.
      // A raw Listener rather than a GestureDetector: InteractiveViewer's scale
      // recogniser claims single-pointer drags, so anything competing in the
      // gesture arena never fires. Pointer events are not arbitrated, so this
      // sees the drag whatever the viewer decides to do with it.
      body: Listener(
        // Opaque so the black surround takes pointers too. Deferring to the
        // child means only the photo itself is draggable, and a swipe that
        // starts just outside it does nothing.
        behavior: HitTestBehavior.opaque,
        onPointerMove: (event) {
          if (_zoomed) return;
          setState(() => _dragOffset += event.delta.dy);
        },
        onPointerUp: (_) {
          if (_zoomed) return;
          if (_dragOffset.abs() > 120) {
            Navigator.of(context).pop();
          } else if (_dragOffset != 0) {
            setState(() => _dragOffset = 0);
          }
        },
        child: Center(
          child: Transform.translate(
            offset: Offset(0, _dragOffset),
            child: Hero(
              tag: 'media-${widget.media.id}',
              child: _LocalFile(
                localPath: widget.media.localPath,
                remotePath: widget.media.url,
                placeholder: const CircularProgressIndicator(color: Colors.white),
                builder: (_, file) => InteractiveViewer(
                  transformationController: _transform,
                  minScale: 1,
                  maxScale: 4,
                  // Panning belongs to the zoomed photo; dragging belongs to
                  // the dismiss gesture. They cannot both own it.
                  panEnabled: _zoomed,
                  child: Image.file(file, fit: BoxFit.contain),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ── Voice notes ─────────────────────────────────────────────────────────────

class VoiceBubble extends StatefulWidget {
  final CoupleMessage message;
  final bool mine;
  final VoidCallback? onRetry;

  /// How playback is created. Injectable because `AudioPlayer` reaches a
  /// platform channel, so without this the play, pause, seek and speed paths
  /// can only be exercised on a device.
  final AudioPlayer Function()? playerFactory;

  /// Asks the server for a transcript that may have arrived since. Called on
  /// expand rather than on build, so a thread of voice notes is not a burst of
  /// requests.
  final Future<void> Function()? onRequestTranscript;

  const VoiceBubble({
    super.key,
    required this.message,
    required this.mine,
    this.onRetry,
    this.onRequestTranscript,
    this.playerFactory,
  });

  @override
  State<VoiceBubble> createState() => _VoiceBubbleState();
}

class _VoiceBubbleState extends State<VoiceBubble> {
  AudioPlayer? _player;
  Duration _position = Duration.zero;
  bool _playing = false;
  bool _preparing = false;
  double _speed = 1;
  bool _showTranscript = false;

  @override
  void dispose() {
    _player?.dispose();
    super.dispose();
  }

  MessageMedia? get _media => widget.message.media;

  Future<void> _toggle() async {
    final media = _media;
    if (media == null) return;

    if (_player == null) {
      setState(() => _preparing = true);
      try {
        final file = media.localPath != null
            ? File(media.localPath!)
            : await MediaCache.instance.file(media.url);
        final player = (widget.playerFactory ?? AudioPlayer.new)();
        await player.setFilePath(file.path);
        player.positionStream.listen((p) {
          if (mounted) setState(() => _position = p);
        });
        player.playerStateStream.listen((state) {
          if (!mounted) return;
          setState(() => _playing = state.playing);
          if (state.processingState == ProcessingState.completed) {
            // Rewind rather than leaving the bar full — the natural next
            // action on a voice note is to play it again.
            player.seek(Duration.zero);
            player.pause();
          }
        });
        _player = player;
      } catch (_) {
        if (mounted) setState(() => _preparing = false);
        return;
      }
      if (mounted) setState(() => _preparing = false);
    }

    final player = _player!;
    if (player.playing) {
      await player.pause();
    } else {
      await player.play();
    }
  }

  Future<void> _cycleSpeed() async {
    const speeds = [1.0, 1.5, 2.0];
    final next = speeds[(speeds.indexOf(_speed) + 1) % speeds.length];
    setState(() => _speed = next);
    await _player?.setSpeed(next);
  }

  Future<void> _toggleTranscript() async {
    final expanding = !_showTranscript;
    setState(() => _showTranscript = expanding);
    if (expanding && !(_media?.hasTranscript ?? false)) {
      await widget.onRequestTranscript?.call();
    }
  }

  @override
  Widget build(BuildContext context) {
    final media = _media;
    if (media == null) return const _Unavailable();

    final total = media.duration;
    final fraction = total.inMilliseconds == 0
        ? 0.0
        : (_position.inMilliseconds / total.inMilliseconds).clamp(0.0, 1.0);
    final accent = widget.mine ? Colors.white : AppColors.warmCoral;
    final muted = (widget.mine ? Colors.white : AppColors.softCharcoal)
        .withValues(alpha: 0.35);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _playButton(accent),
            const SizedBox(width: AppSpacing.md),
            Flexible(
              child: GestureDetector(
                key: const Key('voice_waveform'),
                // Opaque, not the default deferToChild. The bars are separated
                // by a couple of pixels of padding, and deferring means a drag
                // that happens to start in one of those gaps hits nothing —
                // the bar is the control, so the whole strip has to take it.
                behavior: HitTestBehavior.opaque,
                // Drag anywhere on the waveform to seek. A separate thumb
                // would be a 6px target on a bar that is already the control.
                onHorizontalDragUpdate: (details) {
                  final width = context.size?.width ?? 1;
                  final ratio = (details.localPosition.dx / width).clamp(0.0, 1.0);
                  _player?.seek(total * ratio);
                },
                child: _Waveform(
                  amplitudes: media.waveform,
                  played: fraction,
                  playedColour: accent,
                  unplayedColour: muted,
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Text(
              _playing || _position > Duration.zero
                  ? _clock(_position)
                  : media.durationLabel,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: widget.mine ? Colors.white70 : AppColors.softCharcoal,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
            if (_player != null) ...[
              const SizedBox(width: AppSpacing.sm),
              GestureDetector(
                onTap: _cycleSpeed,
                child: Text(
                  '${_speed == _speed.roundToDouble() ? _speed.toInt() : _speed}×',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: widget.mine ? Colors.white70 : AppColors.warmCoral,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ],
        ),
        if (widget.message.isPending)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.sm),
            child: LinearProgressIndicator(
              value: (widget.message.uploadProgress ?? 0) > 0
                  ? widget.message.uploadProgress
                  : null,
              minHeight: 2,
              backgroundColor: muted,
              valueColor: AlwaysStoppedAnimation(accent),
            ),
          ),
        if (widget.message.failed && widget.onRetry != null)
          TextButton.icon(
            onPressed: widget.onRetry,
            icon: const Icon(Icons.refresh_rounded, size: 16),
            label: const Text('Retry'),
            style: TextButton.styleFrom(foregroundColor: accent),
          ),
        _transcriptSection(media, accent),
      ],
    );
  }

  Widget _playButton(Color accent) {
    return SizedBox(
      width: 36,
      height: 36,
      child: _preparing
          ? Padding(
              padding: const EdgeInsets.all(8),
              child: CircularProgressIndicator(strokeWidth: 2, color: accent),
            )
          : IconButton(
              padding: EdgeInsets.zero,
              onPressed: _toggle,
              icon: Icon(
                _playing ? Icons.pause_rounded : Icons.play_arrow_rounded,
                color: accent,
              ),
            ),
    );
  }

  /// Tap-to-expand rather than an always-on wall of text. The note is the
  /// message; the transcript is there when someone cannot listen, or wants to
  /// re-read what was said.
  Widget _transcriptSection(MessageMedia media, Color accent) {
    if (media.transcriptStatus == TranscriptStatus.skipped && !media.hasTranscript) {
      return const SizedBox.shrink();
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          onTap: _toggleTranscript,
          child: Padding(
            padding: const EdgeInsets.only(top: AppSpacing.sm),
            child: Text(
              _showTranscript ? 'Hide transcript' : 'Transcript',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: widget.mine ? Colors.white70 : AppColors.warmCoral,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
        if (_showTranscript)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xs),
            child: Text(
              media.hasTranscript
                  ? media.transcript
                  : switch (media.transcriptStatus) {
                      TranscriptStatus.pending => 'Still transcribing…',
                      TranscriptStatus.failed => 'No transcript for this one.',
                      _ => 'No transcript.',
                    },
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: widget.mine ? Colors.white : AppColors.softCharcoal,
                fontStyle: media.hasTranscript ? FontStyle.normal : FontStyle.italic,
              ),
            ),
          ),
      ],
    );
  }

  String _clock(Duration d) {
    final seconds = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '${d.inMinutes}:$seconds';
  }
}

/// Amplitude bars. Played portion in the accent colour, so progress reads at a
/// glance without a scrubber.
class _Waveform extends StatelessWidget {
  final List<int> amplitudes;
  final double played;
  final Color playedColour;
  final Color unplayedColour;

  const _Waveform({
    required this.amplitudes,
    required this.played,
    required this.playedColour,
    required this.unplayedColour,
  });

  @override
  Widget build(BuildContext context) {
    // A note recorded before waveforms existed, or one whose amplitudes did
    // not survive, still needs a bar to scrub along.
    final bars = amplitudes.isEmpty ? List.filled(24, 30) : amplitudes;
    return SizedBox(
      height: 28,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: List.generate(bars.length, (i) {
          final isPlayed = i / bars.length <= played;
          return Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 1),
              child: Container(
                height: 4 + (bars[i] / 100) * 24,
                decoration: BoxDecoration(
                  color: isPlayed ? playedColour : unplayedColour,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}
