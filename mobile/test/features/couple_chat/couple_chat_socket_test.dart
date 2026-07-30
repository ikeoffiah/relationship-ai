/// Live delivery for the couple's thread.
///
/// The socket is receive-only, so none of this can lose a message — messages go
/// over HTTP. What it can lose is *liveness*, and the failures worth testing are
/// the quiet ones: a dropped connection that never reconnects, a stale "Online"
/// after the socket is gone, and a malformed frame taking the thread down.
library;

import 'dart:async';
import 'dart:io';

import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/couple_chat/couple_chat_socket.dart';

/// A stand-in for `dart:io`'s WebSocket.
///
/// Only the handful of members the socket actually touches are implemented;
/// the rest would be noise. `noSuchMethod` covers them so the class can still
/// satisfy the type.
class FakeWebSocket implements WebSocket {
  final _controller = StreamController<dynamic>();
  final sent = <dynamic>[];
  bool closed = false;
  bool throwOnAdd = false;

  void push(dynamic frame) => _controller.add(frame);
  void fail(Object error) => _controller.addError(error);
  Future<void> serverClosed() => _controller.close();

  @override
  void add(dynamic data) {
    if (throwOnAdd) throw StateError('half-open');
    sent.add(data);
  }

  @override
  StreamSubscription<dynamic> listen(
    void Function(dynamic)? onData, {
    Function? onError,
    void Function()? onDone,
    bool? cancelOnError,
  }) => _controller.stream.listen(
    onData,
    onError: onError,
    onDone: onDone,
    cancelOnError: cancelOnError,
  );

  @override
  Future<dynamic> close([int? code, String? reason]) async {
    closed = true;
    if (!_controller.isClosed) {
      // Deliberately not awaited. A single-subscription controller with no
      // listener never completes its `done` future, and closing an unlistened
      // socket is exactly what the code does when it is disposed mid-connect.
      unawaited(_controller.close());
    }
  }

  @override
  noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  late List<Map<String, dynamic>> events;
  late int lostCalls;

  setUp(() {
    events = [];
    lostCalls = 0;
  });

  CoupleChatSocket build({
    required Future<WebSocket> Function(String) connector,
    String? token = 'a-token',
  }) => CoupleChatSocket(
    relationshipId: 'rel-1',
    onEvent: events.add,
    onConnectionLost: () => lostCalls++,
    connector: connector,
    tokenProvider: () async => token,
  );

  test('connecting listens and reports connected', () async {
    final fake = FakeWebSocket();
    final socket = build(connector: (_) async => fake);

    await socket.connect();

    expect(socket.isConnected, isTrue);
    await socket.dispose();
  });

  test('the url carries the relationship and the token', () async {
    String? seen;
    final socket = build(
      connector: (url) async {
        seen = url;
        return FakeWebSocket();
      },
    );

    await socket.connect();

    expect(seen, contains('/ws/couple/rel-1'));
    expect(seen, contains('token=a-token'));
    await socket.dispose();
  });

  test('with no token it does not connect at all', () async {
    var attempted = false;
    final socket = build(
      token: null,
      connector: (_) async {
        attempted = true;
        return FakeWebSocket();
      },
    );

    await socket.connect();

    expect(attempted, isFalse);
    expect(socket.isConnected, isFalse);
  });

  test('frames are decoded and handed on without interpretation', () async {
    final fake = FakeWebSocket();
    final socket = build(connector: (_) async => fake);
    await socket.connect();

    fake.push('{"type":"presence","online":true}');
    await Future<void>.delayed(Duration.zero);

    expect(events.single['type'], 'presence');
    expect(events.single['online'], isTrue);
    await socket.dispose();
  });

  test('a malformed frame does not tear the connection down', () async {
    final fake = FakeWebSocket();
    final socket = build(connector: (_) async => fake);
    await socket.connect();

    fake.push('not json at all');
    fake.push('[1,2,3]'); // valid JSON, wrong shape
    fake.push('{"type":"presence"}');
    await Future<void>.delayed(Duration.zero);

    expect(events, hasLength(1));
    expect(socket.isConnected, isTrue);
    await socket.dispose();
  });

  test('a non-string frame is ignored', () async {
    final fake = FakeWebSocket();
    final socket = build(connector: (_) async => fake);
    await socket.connect();

    fake.push([1, 2, 3]);
    await Future<void>.delayed(Duration.zero);

    expect(events, isEmpty);
    await socket.dispose();
  });

  test('a failed connect schedules a reconnect rather than giving up', () {
    fakeAsync((async) {
      var attempts = 0;
      final socket = build(
        connector: (_) async {
          attempts++;
          if (attempts == 1) throw const SocketException('refused');
          return FakeWebSocket();
        },
      );

      socket.connect();
      async.flushMicrotasks();
      expect(attempts, 1);
      expect(lostCalls, 1);

      async.elapse(const Duration(seconds: 3));
      expect(attempts, 2, reason: 'the first backoff is 2s');
      socket.dispose();
      async.flushTimers();
    });
  });

  test('backoff grows and is capped', () {
    fakeAsync((async) {
      final attemptTimes = <Duration>[];
      var elapsed = Duration.zero;
      final socket = build(
        connector: (_) async {
          attemptTimes.add(elapsed);
          throw const SocketException('still down');
        },
      );

      socket.connect();
      async.flushMicrotasks();

      // 2s, 4s, 8s, 16s, 30s, 30s… — capped so a long outage still recovers
      // promptly once the network returns.
      for (final step in [2, 4, 8, 16, 30, 30]) {
        elapsed += Duration(seconds: step);
        async.elapse(Duration(seconds: step));
        async.flushMicrotasks();
      }

      expect(attemptTimes.length, 7);
      socket.dispose();
      async.flushTimers();
    });
  });

  test('a good connection resets the backoff', () {
    fakeAsync((async) {
      var attempts = 0;
      final sockets = <FakeWebSocket>[];
      final socket = build(
        connector: (_) async {
          attempts++;
          if (attempts == 1) throw const SocketException('refused');
          final fake = FakeWebSocket();
          sockets.add(fake);
          return fake;
        },
      );

      socket.connect();
      async.flushMicrotasks();
      async.elapse(const Duration(seconds: 2));
      async.flushMicrotasks();
      expect(attempts, 2);

      // Connected. Drop it, and the next attempt should be back to the initial
      // 2s rather than continuing to grow from the earlier failure.
      sockets.single.serverClosed();
      async.flushMicrotasks();
      async.elapse(const Duration(seconds: 2));
      async.flushMicrotasks();

      expect(attempts, 3);
      socket.dispose();
      async.flushTimers();
    });
  });

  test('a server-side close reports the connection lost', () async {
    final fake = FakeWebSocket();
    final socket = build(connector: (_) async => fake);
    await socket.connect();

    await fake.serverClosed();
    await Future<void>.delayed(Duration.zero);

    // Without this the app keeps showing a stale "Online" for the whole
    // backoff, because a socket we no longer hold cannot tell us they left.
    expect(lostCalls, 1);
    expect(socket.isConnected, isFalse);
    await socket.dispose();
  });

  test('a stream error also reports the connection lost', () async {
    final fake = FakeWebSocket();
    final socket = build(connector: (_) async => fake);
    await socket.connect();

    fake.fail(const SocketException('reset by peer'));
    await Future<void>.delayed(Duration.zero);

    expect(lostCalls, 1);
    await socket.dispose();
  });

  test('the heartbeat keeps the presence key alive', () {
    fakeAsync((async) {
      final fake = FakeWebSocket();
      final socket = build(connector: (_) async => fake);
      socket.connect();
      async.flushMicrotasks();

      async.elapse(const Duration(seconds: 95));

      // Comfortably inside the server's 90-second window, so one dropped beat
      // does not read as going offline.
      expect(fake.sent.length, 3);
      socket.dispose();
      async.flushTimers();
    });
  });

  test('a heartbeat onto a half-open socket does not throw', () {
    fakeAsync((async) {
      final fake = FakeWebSocket()..throwOnAdd = true;
      final socket = build(connector: (_) async => fake);
      socket.connect();
      async.flushMicrotasks();

      async.elapse(const Duration(seconds: 31));

      expect(fake.sent, isEmpty);
      socket.dispose();
      async.flushTimers();
    });
  });

  test('disposing stops the heartbeat and the reconnect', () {
    fakeAsync((async) {
      var attempts = 0;
      final fake = FakeWebSocket();
      final socket = build(
        connector: (_) async {
          attempts++;
          return fake;
        },
      );
      socket.connect();
      async.flushMicrotasks();

      socket.dispose();
      async.flushMicrotasks();
      async.elapse(const Duration(minutes: 2));

      expect(attempts, 1, reason: 'a disposed socket must not reconnect');
      expect(fake.sent, isEmpty, reason: 'nor keep beating');
      async.flushTimers();
    });
  });

  test('a disposed socket does not report the connection lost', () async {
    final fake = FakeWebSocket();
    final socket = build(connector: (_) async => fake);
    await socket.connect();

    await socket.dispose();
    await Future<void>.delayed(Duration.zero);

    // Closing on purpose is not a lost connection, and reporting it would flip
    // presence to offline on the way out of the screen.
    expect(lostCalls, 0);
  });

  test('connecting after dispose does nothing', () async {
    var attempts = 0;
    final socket = build(
      connector: (_) async {
        attempts++;
        return FakeWebSocket();
      },
    );

    await socket.dispose();
    await socket.connect();

    expect(attempts, 0);
  });

  test('a socket that arrives after dispose is closed rather than kept', () async {
    final fake = FakeWebSocket();
    final completer = Completer<WebSocket>();
    final socket = build(connector: (_) async => completer.future);

    final connecting = socket.connect();
    await socket.dispose();
    completer.complete(fake);
    await connecting;

    // The connect was in flight when the screen went away; holding the socket
    // would leak it and keep the presence key alive.
    expect(fake.closed, isTrue);
    expect(socket.isConnected, isFalse);
  });
}
