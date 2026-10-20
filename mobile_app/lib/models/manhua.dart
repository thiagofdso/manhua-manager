class Manhua {
  final int id;
  final String title;
  final String urlTemplate;
  final int currentChapter;
  final int? updatedAt;

  Manhua({
    required this.id,
    required this.title,
    required this.urlTemplate,
    required this.currentChapter,
    this.updatedAt,
  });

  factory Manhua.fromJson(Map<String, dynamic> json) {
    return Manhua(
      id: json['id'] as int,
      title: json['title'] as String,
      urlTemplate: json['urlTemplate'] as String,
      currentChapter: json['currentChapter'] as int,
      updatedAt: json['updatedAt'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'urlTemplate': urlTemplate,
      'currentChapter': currentChapter,
      if (updatedAt != null) 'updatedAt': updatedAt,
    };
  }

  String targetUrlForChapter(int chapter) {
    return urlTemplate.replaceAll('{chapter}', chapter.toString());
  }

  Manhua copyWith({
    int? id,
    String? title,
    String? urlTemplate,
    int? currentChapter,
    int? updatedAt,
  }) {
    return Manhua(
      id: id ?? this.id,
      title: title ?? this.title,
      urlTemplate: urlTemplate ?? this.urlTemplate,
      currentChapter: currentChapter ?? this.currentChapter,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
