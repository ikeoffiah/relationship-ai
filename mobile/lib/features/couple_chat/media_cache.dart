/// Local cache for decrypted chat media.
///
/// Media arrives from our own proxy rather than from a CDN, because only the
/// server can decrypt it — which means every fetch needs the bearer token and
/// none of it can go through `Image.network`. It also means what lands here is
/// *plaintext*: the photo, in the clear, on the device.
///
/// That matters more than it looks. The app has biometric/PIN lock, and a
/// decrypted photo sitting in a cache directory walks straight around it — the
/// lock screen protects the UI, not the filesystem. So the cache lives in a
/// temporary directory, is excluded from device backups by living there, and
/// is emptied whenever the app locks.
library;

import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:mobile/core/api_services/base_api_service.dart';
import 'package:path_provider/path_provider.dart';

class MediaCache extends BaseApiService {
  MediaCache({super.injectedDio}) : super(receiveTimeout: const Duration(minutes: 2));

  static final MediaCache instance = MediaCache();

  Directory? _root;

  /// In-flight fetches, so a thread scrolling past the same photo twice does
  /// not download it twice.
  final Map<String, Future<File>> _inFlight = {};

  Future<Directory> _directory() async {
    if (_root != null) return _root!;
    // Cache, not documents: the OS may reclaim it under pressure, which is the
    // correct trade for something re-fetchable that we would rather not keep.
    final base = await getTemporaryDirectory();
    final dir = Directory('${base.path}/chat_media');
    if (!dir.existsSync()) dir.createSync(recursive: true);
    _root = dir;
    return dir;
  }

  /// The local file for a media path, downloading it if we do not have it.
  ///
  /// [remotePath] is an API path such as `/api/v1/chat/media/<id>`, and doubles
  /// as the cache key — media is immutable and its id is random, so a file that
  /// exists is always the right file.
  Future<File> file(String remotePath) {
    final existing = _inFlight[remotePath];
    if (existing != null) return existing;

    final future = _fetch(remotePath).whenComplete(() => _inFlight.remove(remotePath));
    _inFlight[remotePath] = future;
    return future;
  }

  Future<File> _fetch(String remotePath) async {
    final dir = await _directory();
    final name = remotePath.replaceAll(RegExp(r'[^A-Za-z0-9]'), '_');
    final target = File('${dir.path}/$name');
    if (target.existsSync() && target.lengthSync() > 0) return target;

    final response = await dio.get<List<int>>(
      remotePath,
      options: Options(responseType: ResponseType.bytes),
    );
    final bytes = response.data;
    if (bytes == null || bytes.isEmpty) {
      throw StateError('empty media response for $remotePath');
    }

    // Written to a sibling first and then renamed, so a fetch interrupted
    // halfway can never leave a truncated file that later reads as a cache hit.
    final temp = File('${target.path}.part');
    await temp.writeAsBytes(bytes, flush: true);
    await temp.rename(target.path);
    return target;
  }

  /// Drop every decrypted file.
  ///
  /// Called when the app locks. Anything still needed is one fetch away, and
  /// the point of the lock is that the contents of the app stop being available
  /// — including to someone who has the handset and a file browser.
  Future<void> clear() async {
    _inFlight.clear();
    try {
      final dir = await _directory();
      if (dir.existsSync()) {
        await dir.delete(recursive: true);
      }
      _root = null;
    } catch (e) {
      // A cache we could not clear is worth knowing about but not worth
      // crashing over — the alternative is an app that will not lock.
      debugPrint('MediaCache.clear failed: $e');
    }
  }
}
