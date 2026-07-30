/// The hold-to-record gestures.
///
/// These exist because holding a button to record means every recording starts
/// with a press that might have been a mis-tap. The tests here are mostly about
/// the ways out: sliding to cancel, locking, and a press too short to be a
/// message. A recording that cannot be abandoned is the failure mode.
library;

import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:record/record.dart';

import 'package:mobile/features/couple_chat/views/voice_recorder.dart';

/// A recorder that writes a real temp file and emits amplitudes on demand,
/// so the widget's own logic is exercised without a microphone.
class _FakeRecorder implements AudioRecorder {
  static bool permitted = true;
  static String? lastPath;
  final _amplitudes = StreamController<Amplitude>.broadcast();

  @override
  Future<bool> hasPermission() async => permitted;

  @override
  Future<void> start(RecordConfig config, {required String path}) async {
    lastPath = path;
    File(path).writeAsBytesSync([0, 1, 2, 3]);
  }

  @override
  Future<String?> stop() async => lastPath;

  @override
  Stream<Amplitude> onAmplitudeChanged(Duration interval) => _amplitudes.stream;

  @override
  Future<void> dispose() async => _amplitudes.close();

  @override
  noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late GlobalKey<VoiceRecorderBarState> key;
  late List<VoiceRecording> completed;
  late List<bool> activeChanges;

  late Directory tempDir;

  setUp(() {
    // A real directory rather than path_provider: that is a platform channel
    // with no implementation here, and an unmocked call hangs the file.
    tempDir = Directory.systemTemp.createTempSync('voice_recorder_test');
    key = GlobalKey<VoiceRecorderBarState>();
    completed = [];
    activeChanges = [];
    _FakeRecorder.permitted = true;
    _FakeRecorder.lastPath = null;
  });

  Future<void> pump(WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: VoiceRecorderBar(
            key: key,
            onComplete: completed.add,
            onActiveChanged: activeChanges.add,
            recorderFactory: _FakeRecorder.new,
            directoryProvider: () async => tempDir,
          ),
        ),
      ),
    );
  }

  /// Flushes the async teardown chain.
  ///
  /// Ending a recording awaits several times over — stop the ticker, cancel the
  /// amplitude subscription, stop and dispose the recorder, delete the file —
  /// and under fake async each of those only advances on a pump.
  Future<void> flush(WidgetTester tester) async {
    for (var i = 0; i < 8; i++) {
      await tester.pump();
    }
  }

  /// Starts a recording and lets it settle.
  ///
  /// Deliberately not `await state.start()`. A testWidgets body runs inside
  /// fake async, where a Future only completes when the clock is advanced — so
  /// awaiting an async call before any `pump` waits for ever. Kicking it off
  /// and pumping is what actually drives it to completion.
  Future<void> startRecording(WidgetTester tester) async {
    unawaited(key.currentState!.start());
    await tester.pump();
    await tester.pump();
  }

  /// Ends a recording a test left running.
  ///
  /// Recording holds a 100ms periodic ticker and a repeating pulse animation.
  /// A test that asserts mid-recording and simply returns leaves both pending,
  /// and the binding waits on them for ever rather than failing — so every
  /// test that starts one has to put it down.
  Future<void> stopRecording(WidgetTester tester) async {
    final state = key.currentState;
    if (state != null && state.isActive) {
      unawaited(state.cancel());
    }
    await flush(tester);
  }

  testWidgets('nothing is shown until recording starts', (tester) async {
    await pump(tester);
    expect(find.byKey(const Key('voice_recorder_bar')), findsNothing);
  });

  testWidgets('starting shows the bar and the cancel hint', (tester) async {
    await pump(tester);

    await startRecording(tester);

    expect(find.byKey(const Key('voice_recorder_bar')), findsOneWidget);
    expect(find.text('Slide to cancel'), findsOneWidget);
    expect(activeChanges, [true]);

    await stopRecording(tester);
  });

  testWidgets('without microphone permission nothing starts', (tester) async {
    _FakeRecorder.permitted = false;
    await pump(tester);

    await startRecording(tester);

    expect(find.byKey(const Key('voice_recorder_bar')), findsNothing);
    expect(activeChanges, isEmpty);
    expect(find.textContaining('microphone access'), findsOneWidget);

    // Let the snack bar's auto-dismiss timer run out. Leaving it pending stalls
    // the test binding at teardown.
    await tester.pump(const Duration(seconds: 5));
  });

  testWidgets('sliding far enough left arms the cancel', (tester) async {
    await pump(tester);
    await startRecording(tester);

    key.currentState!.onDrag(const Offset(-120, 0));
    await tester.pump();

    expect(find.text('Release to cancel'), findsOneWidget);

    await stopRecording(tester);
  });

  testWidgets('a small slide does not arm it', (tester) async {
    await pump(tester);
    await startRecording(tester);

    key.currentState!.onDrag(const Offset(-20, 0));
    await tester.pump();

    expect(find.text('Slide to cancel'), findsOneWidget);

    await stopRecording(tester);
  });

  testWidgets('releasing after a slide cancels and deletes the file', (
    tester,
  ) async {
    await pump(tester);
    await startRecording(tester);
    final path = _FakeRecorder.lastPath!;

    key.currentState!.onDrag(const Offset(-120, 0));
    unawaited(key.currentState!.onRelease());
    await flush(tester);

    expect(completed, isEmpty);
    // A cancelled recording surviving on disk is what the gesture exists to
    // prevent.
    expect(File(path).existsSync(), isFalse);
    expect(activeChanges, [true, false]);
  });

  testWidgets('sliding up locks the recording and frees the finger', (
    tester,
  ) async {
    await pump(tester);
    await startRecording(tester);

    key.currentState!.onDrag(const Offset(0, -90));
    await tester.pump();

    expect(find.text('Recording — tap to send'), findsOneWidget);
    expect(find.byKey(const Key('voice_stop')), findsOneWidget);
    expect(find.byKey(const Key('voice_cancel')), findsOneWidget);

    await stopRecording(tester);
  });

  testWidgets('a release while locked does not end the recording', (
    tester,
  ) async {
    await pump(tester);
    await startRecording(tester);
    key.currentState!.onDrag(const Offset(0, -90));
    await tester.pump();

    unawaited(key.currentState!.onRelease());
    await flush(tester);

    // Locked means the finger is free; only the buttons end it.
    expect(find.byKey(const Key('voice_recorder_bar')), findsOneWidget);
    expect(completed, isEmpty);

    await stopRecording(tester);
  });

  testWidgets('the stop button while locked sends it', (tester) async {
    await pump(tester);
    await startRecording(tester);
    key.currentState!.onDrag(const Offset(0, -90));
    await tester.pump();
    // Past the one-second floor.
    await tester.pump(const Duration(milliseconds: 1200));

    await tester.tap(find.byKey(const Key('voice_stop')));
    await flush(tester);

    expect(completed, hasLength(1));
    expect(completed.single.durationMs, greaterThanOrEqualTo(1000));
  });

  testWidgets('the discard button while locked throws it away', (tester) async {
    await pump(tester);
    await startRecording(tester);
    key.currentState!.onDrag(const Offset(0, -90));
    await tester.pump(const Duration(milliseconds: 1200));

    await tester.tap(find.byKey(const Key('voice_cancel')));
    await flush(tester);

    expect(completed, isEmpty);
  });

  testWidgets('a press too short to be a message is discarded', (tester) async {
    await pump(tester);
    await startRecording(tester);
    await tester.pump(const Duration(milliseconds: 300));
    final path = _FakeRecorder.lastPath!;

    unawaited(key.currentState!.onRelease());
    await flush(tester);

    expect(completed, isEmpty);
    expect(File(path).existsSync(), isFalse);
  });

  testWidgets('a real recording completes with a duration', (tester) async {
    await pump(tester);
    await startRecording(tester);
    await tester.pump(const Duration(milliseconds: 1500));

    unawaited(key.currentState!.onRelease());
    await flush(tester);

    expect(completed, hasLength(1));
    expect(completed.single.durationMs, greaterThanOrEqualTo(1000));
    expect(completed.single.path, isNotEmpty);
    expect(activeChanges, [true, false]);
  });

  testWidgets('recording stops itself at the two-minute ceiling', (
    tester,
  ) async {
    await pump(tester);
    await startRecording(tester);

    await tester.pump(kMaxVoiceDuration + const Duration(seconds: 1));
    await flush(tester);

    // Stopped here rather than rejected after the upload, so the person can
    // still see why.
    expect(completed, hasLength(1));
    expect(find.byKey(const Key('voice_recorder_bar')), findsNothing);
  });

  testWidgets('dragging before starting does nothing', (tester) async {
    await pump(tester);

    key.currentState!.onDrag(const Offset(-200, 0));
    await tester.pump();

    expect(find.byKey(const Key('voice_recorder_bar')), findsNothing);
  });

  testWidgets('releasing before starting does nothing', (tester) async {
    await pump(tester);

    unawaited(key.currentState!.onRelease());
    await flush(tester);

    expect(completed, isEmpty);
  });
}
