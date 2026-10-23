class ImportWorkItem {
  final String title;
  final String urlTemplate;
  final int? lastChapter;
  final bool alreadyExists;

  ImportWorkItem({
    required this.title,
    required this.urlTemplate,
    this.lastChapter,
    required this.alreadyExists,
  });

  factory ImportWorkItem.fromJson(Map<String, dynamic> json) {
    return ImportWorkItem(
      title: json['title'] ?? '',
      urlTemplate: json['urlTemplate'] ?? '',
      lastChapter: json['lastChapter'] != null ? (json['lastChapter'] as num).toInt() : null,
      alreadyExists: json['alreadyExists'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'urlTemplate': urlTemplate,
      if (lastChapter != null) 'lastChapter': lastChapter,
    };
  }
}

class ImportBrowseResult {
  final String domain;
  final int page;
  final int totalPages;
  final List<ImportWorkItem> items;

  ImportBrowseResult({
    required this.domain,
    required this.page,
    required this.totalPages,
    required this.items,
  });

  factory ImportBrowseResult.fromJson(Map<String, dynamic> json) {
    final rawList = json['items'] as List<dynamic>? ?? [];
    return ImportBrowseResult(
      domain: json['domain'] ?? '',
      page: (json['page'] as num?)?.toInt() ?? 1,
      totalPages: (json['totalPages'] as num?)?.toInt() ?? 1,
      items: rawList.map((e) => ImportWorkItem.fromJson(e)).toList(),
    );
  }
}

class ImportResponse {
  final String status;
  final int imported;
  final int skipped;

  ImportResponse({
    required this.status,
    required this.imported,
    required this.skipped,
  });

  factory ImportResponse.fromJson(Map<String, dynamic> json) {
    return ImportResponse(
      status: json['status'] ?? 'ok',
      imported: (json['imported'] as num?)?.toInt() ?? 0,
      skipped: (json['skipped'] as num?)?.toInt() ?? 0,
    );
  }
}
