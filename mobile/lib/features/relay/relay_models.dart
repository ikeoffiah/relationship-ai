class RelayMessage {
  final String content;
  final List<String> attachments; // URLs or local paths
  RelayMessage({required this.content, this.attachments = const []});

  Map<String, dynamic> toJson() => {
        'content': content,
        'attachments': attachments,
      };
}

class RelayPreviewResponse {
  final String previewHtml;
  RelayPreviewResponse({required this.previewHtml});

  factory RelayPreviewResponse.fromJson(Map<String, dynamic> json) =>
      RelayPreviewResponse(previewHtml: json['preview_html'] as String);
}
