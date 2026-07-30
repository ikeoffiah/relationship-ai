/// A photo or voice note attached to a message in the couple's thread.
///
/// The bytes never come from the storage vendor directly — they cannot, since
/// the decryption key lives on the server. [url] and [thumbUrl] point at our
/// own endpoints, which decrypt on the way out.
library;

/// Whether a voice note's transcript has arrived yet.
///
/// Transcription happens after the upload responds, so a note is playable long
/// before it is readable. The bubble never waits on this.
enum TranscriptStatus {
  /// Not being transcribed at all — the couple has assistance switched off.
  skipped,

  /// Queued or running.
  pending,

  ok,

  /// Tried and could not. The note is unaffected and still plays.
  failed,
}

TranscriptStatus _transcriptStatus(String? name) => switch (name) {
  'pending' => TranscriptStatus.pending,
  'ok' => TranscriptStatus.ok,
  'failed' => TranscriptStatus.failed,
  _ => TranscriptStatus.skipped,
};

class MessageMedia {
  final String id;

  /// 'image' or 'voice'.
  final String kind;
  final String mime;
  final int byteSize;

  /// Path on our API, not on the storage vendor.
  final String url;
  final String? thumbUrl;

  // Voice.
  final int? durationMs;

  /// Amplitude buckets, 0..100, for drawing the waveform without decoding the
  /// audio. Computed on the sending device.
  final List<int> waveform;
  final String transcript;
  final TranscriptStatus transcriptStatus;

  // Image.
  final int? width;
  final int? height;

  /// Set only on an optimistic bubble: the file on this device, rendered while
  /// the upload is still in flight so the photo appears the moment it is
  /// picked rather than after the network.
  final String? localPath;

  const MessageMedia({
    required this.id,
    required this.kind,
    required this.mime,
    required this.byteSize,
    required this.url,
    required this.thumbUrl,
    required this.durationMs,
    required this.waveform,
    required this.transcript,
    required this.transcriptStatus,
    required this.width,
    required this.height,
    this.localPath,
  });

  factory MessageMedia.fromJson(Map<String, dynamic> json) {
    return MessageMedia(
      id: json['id'] as String,
      kind: json['kind'] as String? ?? 'image',
      mime: json['mime'] as String? ?? '',
      byteSize: json['byte_size'] as int? ?? 0,
      url: json['url'] as String? ?? '',
      thumbUrl: json['thumb_url'] as String?,
      durationMs: json['duration_ms'] as int?,
      waveform: List<int>.from(json['waveform'] as List? ?? const []),
      transcript: json['transcript'] as String? ?? '',
      transcriptStatus: _transcriptStatus(json['transcript_status'] as String?),
      width: json['width'] as int?,
      height: json['height'] as int?,
    );
  }

  /// A stand-in rendered from the local file while the upload runs.
  factory MessageMedia.local({
    required String kind,
    required String localPath,
    int? durationMs,
    List<int> waveform = const [],
  }) {
    return MessageMedia(
      id: '',
      kind: kind,
      mime: '',
      byteSize: 0,
      url: '',
      thumbUrl: null,
      durationMs: durationMs,
      waveform: waveform,
      transcript: '',
      transcriptStatus: TranscriptStatus.skipped,
      width: null,
      height: null,
      localPath: localPath,
    );
  }

  bool get isVoice => kind == 'voice';
  bool get isImage => kind == 'image';

  /// True while this is a local stand-in rather than something the server holds.
  bool get isLocal => localPath != null;

  bool get hasTranscript =>
      transcriptStatus == TranscriptStatus.ok && transcript.isNotEmpty;

  Duration get duration => Duration(milliseconds: durationMs ?? 0);

  /// mm:ss, the only format a voice note ever needs.
  String get durationLabel {
    final total = duration.inSeconds;
    final minutes = total ~/ 60;
    final seconds = (total % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  /// Aspect ratio for the bubble, so the thread does not reflow when the image
  /// finishes loading. Falls back to 4:3 for a local file we have not measured.
  double get aspectRatio {
    if (width == null || height == null || height == 0) return 4 / 3;
    return width! / height!;
  }

  MessageMedia copyWith({
    String? transcript,
    TranscriptStatus? transcriptStatus,
  }) {
    return MessageMedia(
      id: id,
      kind: kind,
      mime: mime,
      byteSize: byteSize,
      url: url,
      thumbUrl: thumbUrl,
      durationMs: durationMs,
      waveform: waveform,
      transcript: transcript ?? this.transcript,
      transcriptStatus: transcriptStatus ?? this.transcriptStatus,
      width: width,
      height: height,
      localPath: localPath,
    );
  }
}
