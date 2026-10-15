(() => {
    const editor = document.getElementById('ata-editor');
    const stateLabel = document.getElementById('ata-save-state');
    const contentInput = document.getElementById('id_conteudo');
    const initial = document.getElementById('ata-conteudo-json');
    const content = initial ? JSON.parse(initial.textContent) : {};
    const rosterElement = document.getElementById('ata-integrantes-json');
    const registeredPeople = rosterElement ? JSON.parse(rosterElement.textContent) : [];

    const clone = (value) => JSON.parse(JSON.stringify(value));
    const normalizeName = (name) => name.trim().toLocaleLowerCase();
    const id = () => window.crypto?.randomUUID
        ? window.crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const ensure = (object, key, fallback) => {
        if (object[key] === undefined || object[key] === null) object[key] = clone(fallback);
        return object[key];
    };
    const setValue = (selector, value) => {
        const field = document.querySelector(selector);
        if (field) field.value = value || '';
    };

    if (editor && contentInput) {
        ensure(content, 'participantes', { presentes: [], ausentes: [] });
        ensure(content.participantes, 'presentes', []);
        ensure(content.participantes, 'ausentes', []);
        ensure(content, 'assuntos', { itens: [], observacoes: '' });
        ensure(content.assuntos, 'itens', []);
        ensure(content, 'decisoes', { itens: [], justificativas: '' });
        ensure(content.decisoes, 'itens', []);
        ensure(content, 'acoes', []);
        ensure(content, 'pendencias', { itens: [], proximos_passos: '' });
        ensure(content.pendencias, 'itens', []);
        ensure(content, 'encerramento', { horario_termino: '', proxima_reuniao: '' });
        ensure(content, 'anotacoes', '');
        ensure(content, 'horario_automatico', true);

        setValue('[data-content-field="assuntos.observacoes"]', content.assuntos.observacoes);
        setValue('[data-content-field="decisoes.justificativas"]', content.decisoes.justificativas);
        setValue('[data-content-field="pendencias.proximos_passos"]', content.pendencias.proximos_passos);
        setValue('[data-content-field="encerramento.horario_termino"]', content.encerramento.horario_termino);
        setValue('[data-content-field="encerramento.proxima_reuniao"]', content.encerramento.proxima_reuniao);
        setValue('[data-content-field="anotacoes"]', content.anotacoes);
        document.querySelector('[data-auto-time]').checked = content.horario_automatico;

        function addTextField(parent, labelText, value, className = 'form-control') {
            const field = document.createElement('div');
            field.className = 'mb-2';
            const label = document.createElement('label');
            label.className = 'form-label';
            label.textContent = labelText;
            const input = document.createElement('textarea');
            input.className = className;
            input.rows = 2;
            input.value = value || '';
            field.append(label, input);
            parent.append(field);
            return input;
        }

        function renderPeople(listName) {
            const root = document.querySelector(`[data-people-list="${listName}"]`);
            const names = [...new Map([
                ...registeredPeople,
                ...content.participantes.presentes,
                ...content.participantes.ausentes,
            ].map((name) => [normalizeName(name), name.trim()])).values()];
            root.replaceChildren();
            const checkList = document.createElement('div');
            checkList.className = 'd-grid gap-2';
            names.forEach((name, index) => {
                const item = document.createElement('div');
                item.className = 'form-check';
                const checkbox = document.createElement('input');
                checkbox.className = 'form-check-input';
                checkbox.type = 'checkbox';
                checkbox.id = `ata-${listName}-${index}`;
                checkbox.dataset.participantCheckbox = '';
                checkbox.dataset.participantList = listName;
                checkbox.dataset.personName = name;
                checkbox.checked = content.participantes[listName]
                    .some((selected) => normalizeName(selected) === normalizeName(name));
                const label = document.createElement('label');
                label.className = 'form-check-label';
                label.htmlFor = checkbox.id;
                label.textContent = name;
                item.append(checkbox, label);
                checkList.append(item);
            });
            root.append(checkList);
        }

        function renderRows(kind) {
            const root = document.querySelector(`[data-repeat-list="${kind}"]`);
            root.replaceChildren();
            const rows = kind === 'assuntos' ? content.assuntos.itens
                : kind === 'decisoes' ? content.decisoes.itens
                    : kind === 'pendencias' ? content.pendencias.itens : content.acoes;
            rows.forEach((item, index) => {
                const card = document.createElement('div');
                card.className = 'ata-repeat-row';
                const heading = document.createElement('div');
                heading.className = 'd-flex justify-content-between align-items-center mb-2';
                const title = document.createElement('strong');
                title.textContent = `${kind === 'assuntos' ? 'Assunto' : kind === 'decisoes' ? 'Decisão' : kind === 'acoes' ? 'Ação' : 'Pendência'} ${index + 1}`;
                const remove = document.createElement('button');
                remove.type = 'button';
                remove.className = 'btn btn-outline-danger btn-sm';
                remove.textContent = 'Remover';
                remove.dataset.removeRow = kind;
                remove.dataset.index = index;
                heading.append(title, remove);
                card.append(heading);

                if (kind === 'assuntos') {
                    addTextField(card, 'Título do assunto', item.titulo);
                    addTextField(card, 'Discussão', item.discussao);
                } else if (kind === 'decisoes') {
                    addTextField(card, 'Decisão', item);
                } else if (kind === 'pendencias') {
                    addTextField(card, 'Pendência', item);
                } else {
                    const task = addTextField(card, 'Tarefa', item.tarefa);
                    task.rows = 2;
                    const row = document.createElement('div');
                    row.className = 'row g-2';
                    const responsible = document.createElement('div');
                    responsible.className = 'col-md-6';
                    const responsibleLabel = document.createElement('label');
                    responsibleLabel.className = 'form-label';
                    responsibleLabel.textContent = 'Responsável';
                    const responsibleInput = document.createElement('input');
                    responsibleInput.className = 'form-control';
                    responsibleInput.value = item.responsavel || '';
                    responsible.append(responsibleLabel, responsibleInput);
                    const deadline = document.createElement('div');
                    deadline.className = 'col-md-6';
                    const deadlineLabel = document.createElement('label');
                    deadlineLabel.className = 'form-label';
                    deadlineLabel.textContent = 'Prazo';
                    const deadlineInput = document.createElement('input');
                    deadlineInput.className = 'form-control';
                    deadlineInput.type = 'date';
                    deadlineInput.value = item.prazo || '';
                    deadline.append(deadlineLabel, deadlineInput);
                    row.append(responsible, deadline);
                    card.append(row);

                    const statusGroup = document.createElement('div');
                    statusGroup.className = 'mt-2';
                    const statusLabel = document.createElement('label');
                    statusLabel.className = 'form-label';
                    statusLabel.textContent = 'Status';
                    const status = document.createElement('select');
                    status.className = 'form-select';
                    ['Pendente', 'Em andamento', 'Concluída'].forEach((value) => {
                        const option = document.createElement('option');
                        option.value = value;
                        option.textContent = value;
                        option.selected = item.status === value;
                        status.append(option);
                    });
                    if (!item.status) status.value = 'Pendente';
                    statusGroup.append(statusLabel, status);
                    card.append(statusGroup);

                    const reminderRow = document.createElement('div');
                    reminderRow.className = 'row g-2 mt-1';
                    const reminderDate = document.createElement('div');
                    reminderDate.className = 'col-md-6';
                    const reminderDateLabel = document.createElement('label');
                    reminderDateLabel.className = 'form-label';
                    reminderDateLabel.textContent = 'Data do lembrete';
                    const reminderDateInput = document.createElement('input');
                    reminderDateInput.className = 'form-control';
                    reminderDateInput.type = 'date';
                    reminderDateInput.value = item.lembrete?.data || '';
                    reminderDate.append(reminderDateLabel, reminderDateInput);
                    const reminderTime = document.createElement('div');
                    reminderTime.className = 'col-md-6';
                    const reminderTimeLabel = document.createElement('label');
                    reminderTimeLabel.className = 'form-label';
                    reminderTimeLabel.textContent = 'Hora do lembrete';
                    const reminderTimeInput = document.createElement('input');
                    reminderTimeInput.className = 'form-control';
                    reminderTimeInput.type = 'time';
                    reminderTimeInput.value = item.lembrete?.hora || '';
                    reminderTime.append(reminderTimeLabel, reminderTimeInput);
                    reminderRow.append(reminderDate, reminderTime);
                    card.append(reminderRow);
                }

                card.dataset.rowKind = kind;
                if (item.id) card.dataset.id = item.id;
                root.append(card);
            });
        }

        function addRow(kind) {
            if (kind === 'assuntos') content.assuntos.itens.push({ id: id(), titulo: '', discussao: '' });
            else if (kind === 'decisoes') content.decisoes.itens.push('');
            else if (kind === 'pendencias') content.pendencias.itens.push('');
            else content.acoes.push({
                id: id(),
                tarefa: '',
                responsavel: '',
                prazo: '',
                status: 'Pendente',
                lembrete: { data: '', hora: '' },
            });
            renderRows(kind);
        }

        ['presentes', 'ausentes'].forEach(renderPeople);
        ['assuntos', 'decisoes', 'acoes', 'pendencias'].forEach((kind) => {
            if (!document.querySelector(`[data-repeat-list="${kind}"]`).children.length) {
                if (kind === 'assuntos') {
                    content.assuntos.itens.push({ id: id(), titulo: '', discussao: '' });
                } else if (kind === 'decisoes') content.decisoes.itens.push('');
                else if (kind === 'pendencias') content.pendencias.itens.push('');
                else content.acoes.push({
                    id: id(), tarefa: '', responsavel: '', prazo: '',
                    status: 'Pendente', lembrete: { data: '', hora: '' },
                });
            }
            renderRows(kind);
        });

        function syncContent() {
            content.assuntos.itens = [...document.querySelectorAll('[data-row-kind="assuntos"]')].map((row) => {
                const fields = row.querySelectorAll('textarea');
                return { id: row.dataset.id || id(), titulo: fields[0].value, discussao: fields[1].value };
            });
            content.decisoes.itens = [...document.querySelectorAll('[data-row-kind="decisoes"] textarea')].map((field) => field.value);
            content.pendencias.itens = [...document.querySelectorAll('[data-row-kind="pendencias"] textarea')].map((field) => field.value);
            content.acoes = [...document.querySelectorAll('[data-row-kind="acoes"]')].map((row) => {
                const fields = row.querySelectorAll('textarea, input, select');
                const old = content.acoes.find((acao) => acao.id === row.dataset.id);
                return {
                    id: row.dataset.id || old?.id || id(),
                    tarefa: fields[0].value,
                    responsavel: fields[1].value,
                    prazo: fields[2].value,
                    status: fields[3].value,
                    lembrete: { data: fields[4].value, hora: fields[5].value },
                };
            });
            content.participantes.presentes = [...document.querySelectorAll(
                '[data-people-list="presentes"] [data-participant-checkbox]:checked'
            )].map((checkbox) => checkbox.dataset.personName);
            content.participantes.ausentes = [...document.querySelectorAll(
                '[data-people-list="ausentes"] [data-participant-checkbox]:checked'
            )].map((checkbox) => checkbox.dataset.personName);
            content.assuntos.observacoes = document.querySelector('[data-content-field="assuntos.observacoes"]').value;
            content.decisoes.justificativas = document.querySelector('[data-content-field="decisoes.justificativas"]').value;
            content.pendencias.proximos_passos = document.querySelector('[data-content-field="pendencias.proximos_passos"]').value;
            content.encerramento.horario_termino = document.querySelector('[data-content-field="encerramento.horario_termino"]').value;
            content.encerramento.proxima_reuniao = document.querySelector('[data-content-field="encerramento.proxima_reuniao"]').value;
            content.anotacoes = document.querySelector('[data-content-field="anotacoes"]').value;
            content.horario_automatico = document.querySelector('[data-auto-time]').checked;
            contentInput.value = JSON.stringify(content);
        }

        function scheduleAutosave() {
            syncContent();
            stateLabel.textContent = 'Alterações pendentes…';
            clearTimeout(editor.saveTimer);
            editor.saveTimer = setTimeout(save, 900);
        }

        let saving = false;
        let dirty = false;
        async function save() {
            if (saving) {
                dirty = true;
                return;
            }
            syncContent();
            saving = true;
            dirty = false;
            stateLabel.textContent = 'Salvando…';
            try {
                const response = await fetch(editor.action, {
                    method: 'POST',
                    body: new FormData(editor),
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    credentials: 'same-origin',
                });
                const result = await response.json();
                if (!response.ok || !result.ok) {
                    const message = Object.values(result.errors || {}).flat().join(' ');
                    throw new Error(message || 'Não foi possível salvar a ata.');
                }
                if (result.url && editor.action !== result.url) {
                    editor.action = result.url;
                    window.history.replaceState({}, '', result.url);
                }
                stateLabel.textContent = 'Salvo automaticamente.';
            } catch (error) {
                stateLabel.textContent = error.message || 'Erro ao salvar.';
            } finally {
                saving = false;
                if (dirty) save();
            }
        }

        editor.addEventListener('submit', (event) => {
            event.preventDefault();
            clearTimeout(editor.saveTimer);
            save();
        });
        editor.addEventListener('change', (event) => {
            const checkbox = event.target.closest('[data-participant-checkbox]');
            if (checkbox?.checked) {
                const otherList = checkbox.dataset.participantList === 'presentes'
                    ? 'ausentes'
                    : 'presentes';
                document.querySelectorAll(
                    `[data-people-list="${otherList}"] [data-participant-checkbox]`
                ).forEach((otherCheckbox) => {
                    if (normalizeName(otherCheckbox.dataset.personName)
                        === normalizeName(checkbox.dataset.personName)) {
                        otherCheckbox.checked = false;
                    }
                });
            }
            scheduleAutosave();
        });
        editor.addEventListener('input', scheduleAutosave);
        editor.addEventListener('click', (event) => {
            const add = event.target.closest('[data-add-row]');
            if (add) {
                syncContent();
                addRow(add.dataset.addRow);
                scheduleAutosave();
                return;
            }
            const removeRow = event.target.closest('[data-remove-row]');
            if (removeRow) {
                const { index } = removeRow.dataset;
                const kind = removeRow.dataset.removeRow;
                const rows = kind === 'assuntos' ? content.assuntos.itens
                    : kind === 'decisoes' ? content.decisoes.itens
                        : kind === 'pendencias' ? content.pendencias.itens : content.acoes;
                rows.splice(Number(index), 1);
                renderRows(kind);
                scheduleAutosave();
                return;
            }
            if (event.target.closest('[data-set-current-time]')) {
                const now = new Date();
                document.getElementById('id_horario').value = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
                scheduleAutosave();
            }
            if (event.target.closest('[data-insert-time]')) {
                const notes = document.querySelector('[data-content-field="anotacoes"]');
                const now = new Date();
                const prefix = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')} — `;
                const position = notes.selectionStart;
                const insertion = position && notes.value[position - 1] !== '\n' ? `\n${prefix}` : prefix;
                notes.setRangeText(insertion, position, notes.selectionEnd, 'end');
                notes.focus();
                scheduleAutosave();
            }
        });
        editor.addEventListener('keydown', (event) => {
            if (event.target.matches('[data-content-field="anotacoes"]')
                && event.key === 'Enter'
                && !event.shiftKey
                && document.querySelector('[data-auto-time]').checked) {
                event.preventDefault();
                const now = new Date();
                const prefix = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')} — `;
                event.target.setRangeText(`\n${prefix}`, event.target.selectionStart, event.target.selectionEnd, 'end');
                scheduleAutosave();
            }
        });

        document.querySelectorAll('[data-row-kind]').forEach((row) => {
            const kind = row.dataset.rowKind;
            const index = [...row.parentElement.children].indexOf(row);
            const item = kind === 'assuntos' ? content.assuntos.itens[index]
                : kind === 'acoes' ? content.acoes[index] : null;
            if (item?.id) row.dataset.id = item.id;
        });
    }

    document.querySelectorAll('[data-confirm-delete]').forEach((form) => {
        form.addEventListener('submit', (event) => {
            if (!window.confirm('Excluir esta ata? Esta ação não pode ser desfeita.')) event.preventDefault();
        });
    });

    const selectAll = document.querySelector('[data-select-all-atas]');
    if (selectAll) {
        selectAll.addEventListener('click', () => {
            const checks = [...document.querySelectorAll('.ata-export-checkbox')];
            const select = checks.some((check) => !check.checked);
            checks.forEach((check) => { check.checked = select; });
        });
    }

    const exportForm = document.getElementById('exportar-atas-form');
    if (exportForm) {
        exportForm.addEventListener('submit', (event) => {
            const selected = document.querySelectorAll('.ata-export-checkbox:checked').length;
            const formats = exportForm.querySelectorAll('input[name="formatos"]:checked').length;
            if (!selected || !formats) {
                event.preventDefault();
                window.alert('Selecione pelo menos uma ata e um formato de exportação.');
            }
        });
    }

    const notificationButton = document.querySelector('[data-enable-notifications]');
    if (notificationButton && 'Notification' in window) {
        notificationButton.addEventListener('click', async () => {
            const permission = await Notification.requestPermission();
            notificationButton.textContent = permission === 'granted'
                ? 'Avisos ativados enquanto esta página estiver aberta'
                : 'Permita notificações nas configurações do navegador';
            if (permission === 'granted') scheduleNotifications();
        });
        if (Notification.permission === 'granted') scheduleNotifications();
    }

    function scheduleNotifications() {
        document.querySelectorAll('[data-reminder-at]').forEach((element) => {
            const when = Date.parse(element.dataset.reminderAt);
            if (!Number.isFinite(when) || when <= Date.now()) return;
            const delay = Math.min(when - Date.now(), 2147483000);
            window.setTimeout(() => {
                if (when <= Date.now() + 1000 && Notification.permission === 'granted') {
                    new Notification('AfirmaSUS', { body: 'Você tem um lembrete de ação. Acesse o sistema para consultar.' });
                } else {
                    scheduleNotifications();
                }
            }, delay);
        });
    }
})();
