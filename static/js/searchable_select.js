/**
 * Componente Reutilizável de Searchable Select - SST Freedom
 * Suporta busca remota, debounce, paginação, navegação por teclado,
 * portal flutuante (não cortado por cards/overflow), compatibilidade
 * com formsets dinâmicos e disparo nativo de evento 'change'.
 */
(function() {
    'use strict';

    class SearchableSelect {
        constructor(element, options = {}) {
            if (element._searchableSelectInstance) {
                return element._searchableSelectInstance;
            }

            this.element = element;
            this.options = Object.assign({
                searchUrl: element.getAttribute('data-search-url') || '',
                placeholder: element.getAttribute('data-placeholder') || element.getAttribute('placeholder') || 'Pesquise ou selecione...',
                clearable: element.getAttribute('data-clearable') !== 'false',
                minChars: parseInt(element.getAttribute('data-min-chars') || '0', 10),
                pageSize: parseInt(element.getAttribute('data-page-size') || '20', 10),
                dependentTarget: element.getAttribute('data-dependent-target') || null,
                dependentUrl: element.getAttribute('data-dependent-url') || null,
            }, options);

            this.currentPage = 1;
            this.hasMore = false;
            this.isLoading = false;
            this.currentQuery = '';
            this.items = [];
            this.focusedIndex = -1;
            this.debounceTimer = null;

            this.init();
            element._searchableSelectInstance = this;
        }

        init() {
            // Oculta o elemento original mas mantém no DOM para submissão de formulários
            this.element.style.display = 'none';
            this.element.setAttribute('aria-hidden', 'true');

            // Cria o wrapper do controle
            this.wrapper = document.createElement('div');
            this.wrapper.className = 'searchable-select-wrapper';

            // Determina valor e texto inicial a partir de options selecionadas ou data-attributes
            let initialId = this.element.getAttribute('data-initial-id') || this.element.value || '';
            let initialText = this.element.getAttribute('data-initial-text') || '';

            if (this.element.tagName === 'SELECT' && !initialText && this.element.selectedOptions.length > 0) {
                const opt = this.element.selectedOptions[0];
                if (opt.value) {
                    initialId = opt.value;
                    initialText = opt.textContent.trim();
                }
            }

            // HTML do controle visual no wrapper
            this.wrapper.innerHTML = `
                <div class="searchable-select-control" tabindex="0" role="combobox" aria-expanded="false">
                    <div class="searchable-select-value ${!initialText ? 'searchable-select-placeholder' : ''}">
                        ${initialText ? this.escapeHtml(initialText) : this.escapeHtml(this.options.placeholder)}
                    </div>
                    <div class="searchable-select-indicators">
                        ${this.options.clearable ? `<span class="searchable-select-clear" title="Limpar seleção" style="${initialId ? 'display: inline-block;' : 'display: none;'}"><i class="bi bi-x-lg"></i></span>` : ''}
                        <span class="searchable-select-arrow"><i class="bi bi-chevron-down"></i></span>
                    </div>
                </div>
            `;

            // Dropdown renderizado como portal em document.body para NUNCA ser cortado por overflow de cards ou tabelas
            this.dropdown = document.createElement('div');
            this.dropdown.className = 'searchable-select-dropdown';
            this.dropdown.setAttribute('role', 'listbox');
            this.dropdown.innerHTML = `
                <div class="searchable-select-search">
                    <input type="text" class="searchable-select-input" placeholder="Digite para filtrar..." autocomplete="off">
                </div>
                <ul class="searchable-select-options">
                    <li class="searchable-select-status">Digite para buscar...</li>
                </ul>
                <div class="searchable-select-load-more" style="display: none;">
                    <button type="button" class="searchable-select-load-more-btn">Carregar mais resultados</button>
                </div>
            `;
            document.body.appendChild(this.dropdown);

            // Insere o wrapper visual imediatamente após o elemento original
            this.element.parentNode.insertBefore(this.wrapper, this.element.nextSibling);

            // Mapeia referências do DOM
            this.control = this.wrapper.querySelector('.searchable-select-control');
            this.valueDisplay = this.wrapper.querySelector('.searchable-select-value');
            this.clearBtn = this.wrapper.querySelector('.searchable-select-clear');
            this.searchInput = this.dropdown.querySelector('.searchable-select-input');
            this.optionsList = this.dropdown.querySelector('.searchable-select-options');
            this.loadMoreContainer = this.dropdown.querySelector('.searchable-select-load-more');
            this.loadMoreBtn = this.dropdown.querySelector('.searchable-select-load-more-btn');

            this.bindEvents();
        }

        bindEvents() {
            // Abrir dropdown ao clicar no controle
            this.control.addEventListener('click', (e) => {
                if (this.element.disabled) return;
                if (e.target.closest('.searchable-select-clear')) {
                    this.clear();
                    return;
                }
                this.toggle();
            });

            // Teclado no controle
            this.control.addEventListener('keydown', (e) => {
                if (this.element.disabled) return;
                if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.open();
                }
            });

            // Digitação na caixa de busca com debounce
            this.searchInput.addEventListener('input', () => {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => {
                    this.currentPage = 1;
                    this.currentQuery = this.searchInput.value.trim();
                    this.fetchData(false);
                }, 250);
            });

            // Teclado no input de busca
            this.searchInput.addEventListener('keydown', (e) => this.handleKeydown(e));

            // Botão de carregar mais
            if (this.loadMoreBtn) {
                this.loadMoreBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (!this.isLoading && this.hasMore) {
                        this.currentPage += 1;
                        this.fetchData(true);
                    }
                });
            }

            // Reposicionamento dinâmico em caso de scroll ou resize
            this._repositionHandler = () => {
                if (this.dropdown && this.dropdown.classList.contains('show')) {
                    const rect = this.control.getBoundingClientRect();
                    const vh = window.innerHeight || document.documentElement.clientHeight;
                    // Se o controle saiu totalmente da tela, fecha o dropdown
                    if (rect.bottom < 0 || rect.top > vh) {
                        this.close();
                    } else {
                        this.positionDropdown();
                    }
                }
            };
            window.addEventListener('scroll', this._repositionHandler, true);
            window.addEventListener('resize', this._repositionHandler);

            // Fechar ao clicar fora (verificando tanto wrapper quanto o portal dropdown)
            this._docClickHandler = (e) => {
                if (!this.wrapper.contains(e.target) && !this.dropdown.contains(e.target)) {
                    this.close();
                }
            };
            document.addEventListener('click', this._docClickHandler);
        }

        positionDropdown() {
            if (!this.dropdown || !this.control) return;
            const rect = this.control.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) return;

            const vh = window.innerHeight || document.documentElement.clientHeight;
            const spaceBelow = vh - rect.bottom;
            const spaceAbove = rect.top;
            const minMenuHeight = 240;
            const openUpwards = spaceBelow < minMenuHeight && spaceAbove > spaceBelow;

            this.dropdown.style.width = `${rect.width}px`;
            this.dropdown.style.left = `${rect.left}px`;

            if (openUpwards) {
                this.dropdown.style.top = 'auto';
                this.dropdown.style.bottom = `${vh - rect.top + 4}px`;
            } else {
                this.dropdown.style.top = `${rect.bottom + 4}px`;
                this.dropdown.style.bottom = 'auto';
            }
        }

        open() {
            if (this.element.disabled || this.dropdown.classList.contains('show')) return;
            
            // Fecha qualquer outro dropdown aberto antes de abrir este
            document.querySelectorAll('.searchable-select-dropdown.show').forEach(dd => {
                if (dd !== this.dropdown) dd.classList.remove('show');
            });
            document.querySelectorAll('.searchable-select-control.active').forEach(ctrl => {
                if (ctrl !== this.control) {
                    ctrl.classList.remove('active');
                    ctrl.setAttribute('aria-expanded', 'false');
                }
            });

            this.positionDropdown();
            this.dropdown.classList.add('show');
            this.control.classList.add('active');
            this.control.setAttribute('aria-expanded', 'true');
            this.searchInput.value = '';
            this.searchInput.focus();
            this.focusedIndex = -1;

            // Carrega dados iniciais ou re-renderiza lista estática
            if (this.items.length === 0 || this.currentQuery !== '') {
                this.currentPage = 1;
                this.currentQuery = '';
                this.fetchData(false);
            } else {
                this.renderOptions(this.items, false);
            }
        }

        close() {
            if (!this.dropdown || !this.dropdown.classList.contains('show')) return;
            this.dropdown.classList.remove('show');
            this.control.classList.remove('active');
            this.control.setAttribute('aria-expanded', 'false');
            this.focusedIndex = -1;
        }

        toggle() {
            if (this.dropdown.classList.contains('show')) {
                this.close();
            } else {
                this.open();
            }
        }

        fetchData(append = false) {
            if (!this.options.searchUrl) {
                // Modo estático: filtra a partir das options do select original
                this.filterStaticOptions(this.currentQuery);
                return;
            }

            this.isLoading = true;
            if (!append) {
                this.optionsList.innerHTML = '<li class="searchable-select-status"><i class="bi bi-hourglass-split spinner-border spinner-border-sm me-2"></i>Carregando...</li>';
            }

            const url = new URL(this.options.searchUrl, window.location.origin);
            url.searchParams.set('q', this.currentQuery);
            url.searchParams.set('page', this.currentPage);
            url.searchParams.set('page_size', this.options.pageSize);

            fetch(url.toString(), { credentials: 'same-origin' })
                .then(res => {
                    if (!res.ok) throw new Error('Erro na requisição: ' + res.status);
                    return res.json();
                })
                .then(data => {
                    this.isLoading = false;
                    const results = data.results || data.items || [];
                    this.hasMore = !!data.has_more;

                    if (append) {
                        this.items = this.items.concat(results);
                    } else {
                        this.items = results;
                    }

                    this.renderOptions(this.items, append);

                    if (this.loadMoreContainer) {
                        this.loadMoreContainer.style.display = this.hasMore ? 'block' : 'none';
                    }
                    this.positionDropdown();
                })
                .catch(err => {
                    this.isLoading = false;
                    this.optionsList.innerHTML = '<li class="searchable-select-status text-danger"><i class="bi bi-exclamation-triangle-fill me-1"></i>Erro ao carregar dados.</li>';
                });
        }

        filterStaticOptions(query) {
            if (this.element.tagName !== 'SELECT') return;
            const q = (query || '').toLowerCase();
            const results = [];
            for (let i = 0; i < this.element.options.length; i++) {
                const opt = this.element.options[i];
                if (!opt.value) continue;
                if (!q || opt.textContent.toLowerCase().includes(q)) {
                    results.push({
                        id: opt.value,
                        text: opt.textContent.trim()
                    });
                }
            }
            this.items = results;
            this.hasMore = false;
            this.renderOptions(results, false);
            if (this.loadMoreContainer) this.loadMoreContainer.style.display = 'none';
            this.positionDropdown();
        }

        renderOptions(items, append = false) {
            if (!append) {
                this.optionsList.innerHTML = '';
            }

            if (items.length === 0) {
                this.optionsList.innerHTML = '<li class="searchable-select-status">Nenhum resultado encontrado.</li>';
                return;
            }

            const currentVal = String(this.element.value || '');
            const fragment = document.createDocumentFragment();

            items.forEach((item, index) => {
                const li = document.createElement('li');
                li.className = 'searchable-select-option';
                li.setAttribute('role', 'option');
                li.setAttribute('data-id', item.id);
                li.setAttribute('data-text', item.text);
                li.dataset.index = index;

                if (String(item.id) === currentVal) {
                    li.classList.add('selected');
                    li.setAttribute('aria-selected', 'true');
                }

                li.innerHTML = this.escapeHtml(item.text);

                li.addEventListener('click', () => {
                    this.select(item.id, item.text, item);
                });

                fragment.appendChild(li);
            });

            this.optionsList.appendChild(fragment);
        }

        select(id, text, itemData = null) {
            const previousVal = this.element.value;
            this.element.value = id;

            // Garante que o option exista no select original para envio no formulário
            if (this.element.tagName === 'SELECT') {
                let found = false;
                for (let i = 0; i < this.element.options.length; i++) {
                    if (String(this.element.options[i].value) === String(id)) {
                        this.element.selectedIndex = i;
                        found = true;
                        break;
                    }
                }
                if (!found && id) {
                    const newOpt = new Option(text, id, true, true);
                    this.element.add(newOpt);
                }
            }

            // Atualiza o display visual
            this.valueDisplay.textContent = text;
            this.valueDisplay.classList.remove('searchable-select-placeholder');
            if (this.clearBtn) {
                this.clearBtn.style.display = 'inline-block';
            }

            this.close();

            // Dispara evento nativo 'change' no elemento original
            if (String(previousVal) !== String(id)) {
                const event = new Event('change', { bubbles: true });
                this.element.dispatchEvent(event);
            }

            // Notifica dependentes caso configurado
            if (this.options.dependentTarget && id) {
                this.updateDependent(id, itemData);
            }
        }

        clear() {
            const previousVal = this.element.value;
            this.element.value = '';

            if (this.element.tagName === 'SELECT') {
                this.element.selectedIndex = -1;
            }

            this.valueDisplay.textContent = this.options.placeholder;
            this.valueDisplay.classList.add('searchable-select-placeholder');
            if (this.clearBtn) {
                this.clearBtn.style.display = 'none';
            }

            this.close();

            if (previousVal !== '') {
                const event = new Event('change', { bubbles: true });
                this.element.dispatchEvent(event);
            }

            if (this.options.dependentTarget) {
                const depEl = document.querySelector(this.options.dependentTarget);
                if (depEl) {
                    depEl.innerHTML = '<option value="" disabled selected>Selecione primeiro o item principal...</option>';
                    depEl.disabled = true;
                    depEl.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        }

        updateDependent(parentId, parentData) {
            const depEl = document.querySelector(this.options.dependentTarget);
            if (!depEl || !this.options.dependentUrl) return;

            depEl.disabled = true;
            depEl.innerHTML = '<option value="" disabled selected>Carregando opções...</option>';

            const url = new URL(this.options.dependentUrl, window.location.origin);
            url.searchParams.set('product_id', parentId);

            fetch(url.toString(), { credentials: 'same-origin' })
                .then(res => res.json())
                .then(data => {
                    depEl.innerHTML = '';
                    const variants = data.variants || [];
                    if (variants.length === 0) {
                        depEl.innerHTML = '<option value="" disabled selected>Nenhum tamanho disponível</option>';
                        depEl.disabled = true;
                    } else {
                        depEl.disabled = false;
                        if (variants.length > 1) {
                            depEl.innerHTML = '<option value="" disabled selected>Selecione o tamanho...</option>';
                        }
                        variants.forEach(v => {
                            const opt = new Option(v.text || v.tamanho, v.id);
                            depEl.add(opt);
                        });
                        if (variants.length === 1) {
                            depEl.value = variants[0].id;
                        }
                    }
                    depEl.dispatchEvent(new Event('change', { bubbles: true }));
                })
                .catch(err => {
                    depEl.innerHTML = '<option value="" disabled selected>Erro ao carregar</option>';
                    depEl.disabled = true;
                });
        }

        handleKeydown(e) {
            const options = Array.from(this.optionsList.querySelectorAll('.searchable-select-option'));
            if (options.length === 0) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.focusedIndex = (this.focusedIndex + 1) % options.length;
                this.updateFocusedOption(options);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.focusedIndex = (this.focusedIndex - 1 + options.length) % options.length;
                this.updateFocusedOption(options);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (this.focusedIndex >= 0 && this.focusedIndex < options.length) {
                    options[this.focusedIndex].click();
                }
            } else if (e.key === 'Escape') {
                e.preventDefault();
                this.close();
                this.control.focus();
            } else if (e.key === 'Tab') {
                this.close();
            }
        }

        updateFocusedOption(options) {
            options.forEach((opt, idx) => {
                if (idx === this.focusedIndex) {
                    opt.classList.add('focused');
                    opt.scrollIntoView({ block: 'nearest' });
                } else {
                    opt.classList.remove('focused');
                }
            });
        }

        escapeHtml(str) {
            if (!str) return '';
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        destroy() {
            if (this._repositionHandler) {
                window.removeEventListener('scroll', this._repositionHandler, true);
                window.removeEventListener('resize', this._repositionHandler);
            }
            if (this._docClickHandler) {
                document.removeEventListener('click', this._docClickHandler);
            }
            if (this.dropdown && this.dropdown.parentNode) {
                this.dropdown.parentNode.removeChild(this.dropdown);
            }
            if (this.wrapper && this.wrapper.parentNode) {
                this.wrapper.parentNode.removeChild(this.wrapper);
            }
            this.element.style.display = '';
            this.element.removeAttribute('aria-hidden');
            delete this.element._searchableSelectInstance;
        }
    }

    // Inicializador global para o DOM e linhas dinâmicas
    window.initSearchableSelects = function(container = document) {
        if (!container) container = document;
        let elements = [];
        if (container.nodeType === Node.ELEMENT_NODE && container.matches('.searchable-select')) {
            elements = [container];
        } else if (container.querySelectorAll) {
            elements = Array.from(container.querySelectorAll('.searchable-select'));
        }

        elements.forEach(el => {
            if (el._searchableSelectInstance) {
                const inst = el._searchableSelectInstance;
                if (document.body.contains(inst.wrapper)) {
                    return; // Já inicializado e ativo no DOM
                } else {
                    inst.destroy();
                }
            }

            // Remove wrapper órfão adjacente se existir (ex: vindo de clone residual)
            const nextEl = el.nextElementSibling;
            if (nextEl && nextEl.classList.contains('searchable-select-wrapper')) {
                nextEl.remove();
            }

            new SearchableSelect(el);
        });
    };

    // Inicializa automaticamente no carregamento da página
    document.addEventListener('DOMContentLoaded', () => {
        window.initSearchableSelects();
    });

    window.SearchableSelect = SearchableSelect;
})();
