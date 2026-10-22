class Manhua {
  final int id;
  final String title;
  final String urlTemplate;
  final int currentChapter;
  final int? updatedAt;
  final int? chapterId;
  final Map<String, dynamic>? nextChapter;
  final Map<String, dynamic>? prevChapter;
  final bool isFavorite;
  final int? customOrder;
  final int? lastChapter;
  final int? updateDay;
  final bool isHiatus;

  Manhua({
    required this.id,
    required this.title,
    required this.urlTemplate,
    required this.currentChapter,
    this.updatedAt,
    this.chapterId,
    this.nextChapter,
    this.prevChapter,
    this.isFavorite = false,
    this.customOrder,
    this.lastChapter,
    this.updateDay,
    this.isHiatus = false,
  });

  factory Manhua.fromJson(Map<String, dynamic> json) {
    return Manhua(
      id: json['id'] as int,
      title: json['title'] as String,
      urlTemplate: json['urlTemplate'] as String,
      currentChapter: json['currentChapter'] as int,
      updatedAt: json['updatedAt'] as int?,
      chapterId: json['chapterId'] as int?,
      nextChapter: json['nextChapter'] != null
          ? Map<String, dynamic>.from(json['nextChapter'] as Map)
          : null,
      prevChapter: json['prevChapter'] != null
          ? Map<String, dynamic>.from(json['prevChapter'] as Map)
          : null,
      isFavorite: (json['isFavorite'] as bool?) ?? false,
      customOrder: json['customOrder'] as int?,
      lastChapter: json['lastChapter'] as int?,
      updateDay: json['updateDay'] as int?,
      isHiatus: (json['isHiatus'] as bool?) ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'urlTemplate': urlTemplate,
      'currentChapter': currentChapter,
      if (updatedAt != null) 'updatedAt': updatedAt,
      if (chapterId != null) 'chapterId': chapterId,
      if (nextChapter != null) 'nextChapter': nextChapter,
      if (prevChapter != null) 'prevChapter': prevChapter,
      'isFavorite': isFavorite,
      if (customOrder != null) 'customOrder': customOrder,
      if (lastChapter != null) 'lastChapter': lastChapter,
      if (updateDay != null) 'updateDay': updateDay,
      'isHiatus': isHiatus,
    };
  }

  String targetUrlForChapter(int chapter) {
    if (urlTemplate.contains('mangafire.to') && chapterId != null && chapter == currentChapter) {
      if (urlTemplate.contains('{chapter}')) {
        return urlTemplate.replaceAll('{chapter}', chapterId.toString());
      }
      return urlTemplate.replaceFirst(RegExp(r'/chapter/\d+'), '/chapter/$chapterId');
    }
    if (urlTemplate.contains('comix.to') && chapterId != null && chapter == currentChapter) {
      if (urlTemplate.contains('{chapter}')) {
        return urlTemplate.replaceAll('{chapter}', '$chapterId-chapter-$chapter');
      }
      return urlTemplate.replaceFirst(RegExp(r'/\d+-chapter-\d+'), '/$chapterId-chapter-$chapter');
    }
    return urlTemplate.replaceAll('{chapter}', chapter.toString());
  }

  Manhua copyWith({
    int? id,
    String? title,
    String? urlTemplate,
    int? currentChapter,
    int? updatedAt,
    int? chapterId,
    Map<String, dynamic>? nextChapter,
    Map<String, dynamic>? prevChapter,
    bool? isFavorite,
    int? customOrder,
    int? lastChapter,
    int? updateDay,
    bool? isHiatus,
  }) {
    return Manhua(
      id: id ?? this.id,
      title: title ?? this.title,
      urlTemplate: urlTemplate ?? this.urlTemplate,
      currentChapter: currentChapter ?? this.currentChapter,
      updatedAt: updatedAt ?? this.updatedAt,
      chapterId: chapterId ?? this.chapterId,
      nextChapter: nextChapter ?? this.nextChapter,
      prevChapter: prevChapter ?? this.prevChapter,
      isFavorite: isFavorite ?? this.isFavorite,
      customOrder: customOrder ?? this.customOrder,
      lastChapter: lastChapter ?? this.lastChapter,
      updateDay: updateDay ?? this.updateDay,
      isHiatus: isHiatus ?? this.isHiatus,
    );
  }
}
