class ImportDomain {
  final String domain;
  final String name;
  final bool supported;

  ImportDomain({
    required this.domain,
    required this.name,
    required this.supported,
  });

  factory ImportDomain.fromJson(Map<String, dynamic> json) {
    return ImportDomain(
      domain: json['domain'] ?? '',
      name: json['name'] ?? '',
      supported: json['supported'] ?? false,
    );
  }
}
