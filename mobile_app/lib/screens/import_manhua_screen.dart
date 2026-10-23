import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/manhua_controller.dart';
import '../models/import_domain.dart';
import '../models/import_work_item.dart';
import '../services/api_service.dart';

class ImportManhuaScreen extends StatefulWidget {
  final ApiService? apiService;

  const ImportManhuaScreen({super.key, this.apiService});

  @override
  State<ImportManhuaScreen> createState() => _ImportManhuaScreenState();
}

class _ImportManhuaScreenState extends State<ImportManhuaScreen> {
  late final ApiService _apiService;
  final TextEditingController _searchController = TextEditingController();

  List<ImportDomain> _domains = [];
  ImportDomain? _selectedDomain;
  bool _isLoadingDomains = true;

  bool _isSearching = false;
  List<ImportWorkItem> _items = [];
  final Set<int> _selectedIndexes = {};
  int _currentPage = 1;
  int _totalPages = 1;
  String? _errorMessage;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _apiService = widget.apiService ?? ApiService();
    _loadDomains();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadDomains() async {
    try {
      final domains = await _apiService.fetchImportDomains();
      if (mounted) {
        setState(() {
          _domains = domains;
          if (domains.isNotEmpty) {
            _selectedDomain = domains.firstWhere(
              (d) => d.supported,
              orElse: () => domains.first,
            );
          }
          _isLoadingDomains = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Falha ao carregar domínios: $e';
          _isLoadingDomains = false;
        });
      }
    }
  }

  Future<void> _search({int page = 1}) async {
    if (_selectedDomain == null || !_selectedDomain!.supported) return;

    setState(() {
      _isSearching = true;
      _errorMessage = null;
      _currentPage = page;
      _selectedIndexes.clear();
    });

    try {
      final result = await _apiService.browseImportWorks(
        domain: _selectedDomain!.domain,
        query: _searchController.text.trim().isEmpty ? null : _searchController.text.trim(),
        page: page,
      );
      if (mounted) {
        setState(() {
          _items = result.items;
          _currentPage = result.page;
          _totalPages = result.totalPages;
          _isSearching = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
          _isSearching = false;
        });
      }
    }
  }

  void _toggleSelectAll(bool? value) {
    setState(() {
      _selectedIndexes.clear();
      if (value == true) {
        for (int i = 0; i < _items.length; i++) {
          if (!_items[i].alreadyExists) {
            _selectedIndexes.add(i);
          }
        }
      }
    });
  }

  Future<void> _submitImport() async {
    final toImport = _selectedIndexes.map((i) => _items[i]).toList();
    if (toImport.isEmpty) return;

    setState(() {
      _isSubmitting = true;
    });

    try {
      final res = await _apiService.importWorks(toImport);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${res.imported} obras importadas com sucesso! (${res.skipped} ignoradas)'),
            backgroundColor: Colors.green,
          ),
        );
        try {
          context.read<ManhuaController>().loadManhuas();
        } catch (_) {}
        _search(page: _currentPage);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Erro ao importar: $e'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final canSelectCount = _items.where((i) => !i.alreadyExists).length;
    final allSelected = canSelectCount > 0 && _selectedIndexes.length == canSelectCount;

    return Scaffold(
      backgroundColor: const Color(0xFF121214),
      appBar: AppBar(
        title: const Text('Importar Obras'),
        backgroundColor: const Color(0xFF202024),
      ),
      body: _isLoadingDomains
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Dropdown de Domínios
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF202024),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFF323238)),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<ImportDomain>(
                        value: _selectedDomain,
                        isExpanded: true,
                        dropdownColor: const Color(0xFF202024),
                        items: _domains.map((d) {
                          return DropdownMenuItem<ImportDomain>(
                            value: d,
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    d.name.isNotEmpty ? d.name : d.domain,
                                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w500),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: d.supported ? Colors.green.withOpacity(0.2) : Colors.redAccent.withOpacity(0.2),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Text(
                                    d.supported ? 'Suportado' : 'Sem suporte',
                                    style: TextStyle(
                                      color: d.supported ? Colors.greenAccent : Colors.redAccent,
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                        onChanged: (val) {
                          setState(() {
                            _selectedDomain = val;
                            _items.clear();
                            _selectedIndexes.clear();
                            _errorMessage = null;
                          });
                        },
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Barra de Busca + Botão Pesquisar
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _searchController,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            hintText: 'Pesquisar obra...',
                            hintStyle: const TextStyle(color: Colors.grey),
                            filled: true,
                            fillColor: const Color(0xFF202024),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8),
                              borderSide: const BorderSide(color: Color(0xFF323238)),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8),
                              borderSide: const BorderSide(color: Color(0xFF323238)),
                            ),
                          ),
                          onSubmitted: (_) => _search(page: 1),
                        ),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF8257E6),
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        onPressed: (_selectedDomain?.supported ?? false) && !_isSearching
                            ? () => _search(page: 1)
                            : null,
                        child: _isSearching
                            ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : const Text('Pesquisar', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),

                  // Barra "Selecionar todos"
                  if (_items.isNotEmpty)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF202024),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Row(
                        children: [
                          InkWell(
                            onTap: canSelectCount > 0 ? () => _toggleSelectAll(!allSelected) : null,
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Checkbox(
                                  value: allSelected,
                                  onChanged: canSelectCount > 0 ? _toggleSelectAll : null,
                                  activeColor: const Color(0xFF8257E6),
                                ),
                                const Text('Selecionar todos', style: TextStyle(color: Colors.white, fontSize: 13)),
                              ],
                            ),
                          ),
                          const Spacer(),
                          Text(
                            '${_selectedIndexes.length} selecionadas',
                            style: const TextStyle(color: Colors.grey, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                  const SizedBox(height: 8),

                  // Lista de Obras
                  Expanded(
                    child: _errorMessage != null
                        ? Center(child: Text(_errorMessage!, style: const TextStyle(color: Colors.redAccent)))
                        : _items.isEmpty
                            ? Center(
                                child: Text(
                                  _selectedDomain?.supported == false
                                      ? 'Importação ainda não suportada para este domínio.'
                                      : 'Nenhuma obra carregada. Clique em Pesquisar.',
                                  style: const TextStyle(color: Colors.grey),
                                ),
                              )
                            : ListView.separated(
                                itemCount: _items.length,
                                separatorBuilder: (_, __) => const Divider(color: Color(0xFF29292E), height: 1),
                                itemBuilder: (context, index) {
                                  final item = _items[index];
                                  final isChecked = _selectedIndexes.contains(index);

                                  return ListTile(
                                    contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
                                    leading: Checkbox(
                                      value: item.alreadyExists ? false : isChecked,
                                      onChanged: item.alreadyExists
                                          ? null
                                          : (val) {
                                              setState(() {
                                                if (val == true) {
                                                  _selectedIndexes.add(index);
                                                } else {
                                                  _selectedIndexes.remove(index);
                                                }
                                              });
                                            },
                                      activeColor: const Color(0xFF8257E6),
                                    ),
                                    title: Text(
                                      item.title,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        color: item.alreadyExists ? Colors.grey : Colors.white,
                                        fontWeight: FontWeight.w500,
                                        fontSize: 14,
                                      ),
                                    ),
                                    subtitle: Text(
                                      item.lastChapter != null ? 'Cap. ${item.lastChapter}' : 'Sem capítulos',
                                      style: const TextStyle(color: Colors.grey, fontSize: 12),
                                    ),
                                    trailing: item.alreadyExists
                                        ? Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                            decoration: BoxDecoration(
                                              color: const Color(0xFF29292E),
                                              borderRadius: BorderRadius.circular(4),
                                            ),
                                            child: const Text('Já cadastrada', style: TextStyle(color: Colors.grey, fontSize: 11)),
                                          )
                                        : null,
                                  );
                                },
                              ),
                  ),

                  // Paginação
                  if (_items.isNotEmpty && _totalPages > 1)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8.0),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF202024)),
                            onPressed: _currentPage > 1 ? () => _search(page: _currentPage - 1) : null,
                            child: const Text('◀ Anterior', style: TextStyle(color: Colors.white, fontSize: 12)),
                          ),
                          Text('Página $_currentPage de $_totalPages', style: const TextStyle(color: Colors.grey, fontSize: 12)),
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF202024)),
                            onPressed: _currentPage < _totalPages ? () => _search(page: _currentPage + 1) : null,
                            child: const Text('Próxima ▶', style: TextStyle(color: Colors.white, fontSize: 12)),
                          ),
                        ],
                      ),
                    ),

                  // Botão Importar
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF8257E6),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    onPressed: _selectedIndexes.isNotEmpty && !_isSubmitting ? _submitImport : null,
                    child: _isSubmitting
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : Text(
                            'Importar (${_selectedIndexes.length})',
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                          ),
                  ),
                ],
              ),
            ),
    );
  }
}
