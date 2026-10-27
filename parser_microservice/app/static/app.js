document.addEventListener('DOMContentLoaded', () => {
    const navBtns = document.querySelectorAll('.nav-btn');
    const sections = document.querySelectorAll('.module-section');
    const resultsContainer = document.getElementById('results-container');
    const resultsContent = document.getElementById('results-content');
    const loader = document.getElementById('loader');
    const closeResultsBtn = document.getElementById('close-results');

    // Default dates
    const mod2DateInput = document.getElementById('mod2-date');
    if (mod2DateInput) {
        let d = new Date();
        d.setDate(d.getDate() - 7); 
        mod2DateInput.value = d.toISOString().slice(0, 16);
    }

    // Elements for Projects
    const projectsList = document.getElementById('projects-list');
    const projectDetails = document.getElementById('project-details');
    const pdName = document.getElementById('pd-name');
    const projectLinksList = document.getElementById('project-links-list');
    const btnCreateProject = document.getElementById('btn-create-project');
    const btnDeleteProject = document.getElementById('btn-delete-project');
    const btnAddLink = document.getElementById('btn-add-link');
    const btnScanProject = document.getElementById('btn-scan-project');
    const newLinkUrl = document.getElementById('new-link-url');
    
    let currentProjectId = null;
    let projectsData = [];

    // Load from LocalStorage
    document.querySelectorAll('input').forEach(input => {
        if (input.id && localStorage.getItem(input.id)) {
            input.value = localStorage.getItem(input.id);
        }
        input.addEventListener('change', () => {
            localStorage.setItem(input.id, input.value);
        });
    });

    // Handle project link fast-fill selectors
    document.querySelectorAll('.project-link-selector').forEach(sel => {
        sel.addEventListener('change', (e) => {
            const val = e.target.value;
            if (!val) return; // ignore default option

            const targetUrlId = e.target.getAttribute('data-target-url');
            const targetPlatformId = e.target.getAttribute('data-target-platform');
            
            const urlInput = document.getElementById(targetUrlId);
            const platformSelect = document.getElementById(targetPlatformId);

            if (urlInput) urlInput.value = val;
            if (platformSelect) {
                if (val.includes('yandex.ru')) {
                    platformSelect.value = 'yandex';
                } else if (val.includes('2gis')) {
                    platformSelect.value = 'twogis';
                }
            }
        });
    });

    // --- PROJECTS LOGIC ---
    const fetchProjects = async () => {
        try {
            const res = await fetch('/api/v1/projects');
            if (!res.ok) {
                console.error("Failed to fetch projects:", res.status);
                return;
            }
            const data = await res.json();
            if (Array.isArray(data)) {
                projectsData = data;
                renderProjectsList();
            } else {
                console.error("Projects response is not an array:", data);
            }
        } catch (err) {
            console.error(err);
        }
    };

    const renderProjectsList = () => {
        projectsList.innerHTML = '';
        projectsData.forEach(p => {
            const li = document.createElement('li');
            li.className = `project-item ${p.id === currentProjectId ? 'active' : ''}`;
            li.textContent = p.name;
            li.onclick = () => selectProject(p.id);
            projectsList.appendChild(li);
        });
        
        if (currentProjectId) {
            const p = projectsData.find(x => x.id === currentProjectId);
            if (p) {
                projectDetails.classList.remove('hidden');
                pdName.textContent = p.name;
                renderProjectLinks(p.links);
            } else {
                projectDetails.classList.add('hidden');
            }
        } else {
            projectDetails.classList.add('hidden');
        }
        updateProjectLinkSelectors();
    };

    const updateProjectLinkSelectors = () => {
        const selectors = document.querySelectorAll('.project-link-selector');
        selectors.forEach(sel => {
            // Keep the first default option
            sel.innerHTML = '<option value="">-- Ввести вручную --</option>';
            projectsData.forEach(p => {
                if (p.links && p.links.length > 0) {
                    const optgroup = document.createElement('optgroup');
                    optgroup.label = p.name;
                    p.links.forEach(link => {
                        const option = document.createElement('option');
                        option.value = link;
                        
                        // Create a readable label based on URL
                        let platformText = link;
                        if (link.includes('yandex.ru')) platformText = 'Яндекс Карты';
                        else if (link.includes('2gis')) platformText = '2GIS';
                        
                        // Truncate link for better display
                        const shortLink = link.length > 30 ? link.substring(0, 30) + '...' : link;
                        option.textContent = `${platformText} (${shortLink})`;
                        
                        optgroup.appendChild(option);
                    });
                    sel.appendChild(optgroup);
                }
            });
            
            // Обработчик выбора
            sel.addEventListener('change', (e) => {
                const val = e.target.value;
                if (!val) return;
                
                const targetUrlId = sel.getAttribute('data-target-url');
                const targetPlatformId = sel.getAttribute('data-target-platform');
                
                if (targetUrlId) {
                    document.getElementById(targetUrlId).value = val;
                }
                
                if (targetPlatformId) {
                    const platformSelect = document.getElementById(targetPlatformId);
                    if (val.includes('yandex')) platformSelect.value = 'yandex';
                    else if (val.includes('2gis')) platformSelect.value = 'twogis';
                }
            });
        });
    };

    const renderProjectLinks = (links) => {
        projectLinksList.innerHTML = '';
        links.forEach((link, idx) => {
            const li = document.createElement('li');
            li.className = 'link-item';
            li.innerHTML = `
                <a href="${link}" target="_blank">${link}</a>
                <button class="btn-remove-link" onclick="removeProjectLink(${idx})">&times;</button>
            `;
            projectLinksList.appendChild(li);
        });
    };

    const selectProject = (id) => {
        currentProjectId = id;
        renderProjectsList();
    };

    window.removeProjectLink = async (idx) => {
        const p = projectsData.find(x => x.id === currentProjectId);
        if (!p) return;
        const newLinks = [...p.links];
        newLinks.splice(idx, 1);
        await updateProject(p.id, { links: newLinks });
    };

    const updateProject = async (id, data) => {
        try {
            await fetch(`/api/v1/projects/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            await fetchProjects();
        } catch (err) {
            alert('Ошибка при обновлении проекта');
        }
    };

    btnCreateProject.addEventListener('click', async () => {
        const name = prompt('Введите название нового проекта:');
        if (!name) return;
        try {
            const res = await fetch('/api/v1/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, links: [] })
            });
            const newProj = await res.json();
            currentProjectId = newProj.id;
            await fetchProjects();
        } catch (err) {
            alert('Ошибка при создании проекта');
        }
    });

    btnDeleteProject.addEventListener('click', async () => {
        if (!confirm('Вы уверены, что хотите удалить проект?')) return;
        try {
            await fetch(`/api/v1/projects/${currentProjectId}`, { method: 'DELETE' });
            currentProjectId = null;
            await fetchProjects();
        } catch (err) {
            alert('Ошибка при удалении');
        }
    });

    btnAddLink.addEventListener('click', async () => {
        const url = newLinkUrl.value.trim();
        if (!url) return;
        const p = projectsData.find(x => x.id === currentProjectId);
        if (!p) return;
        
        const newLinks = [...p.links, url];
        await updateProject(p.id, { links: newLinks });
        newLinkUrl.value = '';
    });

    btnScanProject.addEventListener('click', async () => {
        if (!currentProjectId) return;
        navBtns.forEach(b => b.classList.remove('active'));
        sections.forEach(s => s.classList.remove('active'));
        try {
            showLoading();
            const res = await fetch(`/api/v1/projects/${currentProjectId}/scan`, { method: 'POST' });
            const data = await res.json();
            
            if (res.ok) {
                let html = `<h2>Сводка по проекту</h2>`;
                data.results.forEach(r => {
                    if (r.status !== 'success') {
                        html += `
                            <div class="scan-result-card">
                                <div class="scan-result-header">
                                    <a href="${r.url}" class="scan-result-url" target="_blank">${r.url}</a>
                                    <span class="status-badge status-error">Ошибка: ${r.error_message}</span>
                                </div>
                            </div>
                        `;
                        return;
                    }
                    
                    let reviewsHtml = '';
                    if (r.new_reviews && r.new_reviews.length > 0) {
                        reviewsHtml = `<div class="scan-result-reviews"><h4>Новые отзывы (за 30 дней):</h4><div class="reviews-grid">`;
                        r.new_reviews.forEach(rev => {
                            reviewsHtml += `
                                <div class="review-card">
                                    <div class="review-header">
                                        <span>👤 ${rev.author || 'Аноним'}</span>
                                        <span class="review-rating">${rev.rating ? rev.rating + '★' : ''}</span>
                                    </div>
                                    <div class="review-date">${rev.date_parsed ? rev.date_parsed.split('T')[0] : rev.date_raw}</div>
                                    <div class="review-text">${rev.text || ''}</div>
                                </div>
                            `;
                        });
                        reviewsHtml += `</div></div>`;
                    } else {
                        reviewsHtml = `<p style="color:var(--text-muted); margin-top:1rem;">Новых отзывов нет.</p>`;
                    }

                    html += `
                        <div class="scan-result-card">
                            <div class="scan-result-header">
                                <a href="${r.url}" class="scan-result-url" target="_blank">${r.url}</a>
                                <span class="status-badge status-success">Успешно</span>
                            </div>
                            <div class="scan-result-stats">
                                <span>⭐ ${r.rating || 'N/A'}</span>
                                <span>📝 ${r.reviews_count || 0} оценок</span>
                            </div>
                            ${reviewsHtml}
                        </div>
                    `;
                });
                resultsContent.innerHTML = html;
            } else {
                handleError(data.detail || "Error scanning project");
            }
        } catch (err) {
            handleError(err);
        } finally {
            loader.classList.add('hidden');
            resultsContent.classList.remove('hidden');
        }
    });

    // Initial fetch
    fetchProjects();

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (!btn.dataset.target) return; // Prevent crash for group toggles
            
            navBtns.forEach(b => b.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));
            btn.classList.add('active');
            
            // Also mark the parent toggle as active if it's a sub-button
            const group = btn.closest('.nav-group');
            if (group) {
                const toggle = group.querySelector('.nav-group-toggle');
                if (toggle) toggle.classList.add('active');
            }
            
            document.getElementById(btn.dataset.target).classList.add('active');
            resultsContainer.classList.add('hidden');
            
            if (btn.dataset.target === 'module-history') {
                if (typeof window.fetchHistory === 'function') window.fetchHistory();
            }
            if (btn.dataset.target === 'module-competitor-history') {
                if (typeof window.fetchCompetitorHistory === 'function') window.fetchCompetitorHistory();
            }
            if (btn.dataset.target === 'module-mentions-history') {
                if (typeof window.fetchMentionsHistory === 'function') window.fetchMentionsHistory();
            }
        });
    });

    closeResultsBtn.addEventListener('click', () => {
        resultsContainer.classList.add('hidden');
    });

    const showLoading = () => {
        resultsContainer.classList.remove('hidden');
        loader.classList.remove('hidden');
        
        // Reset loader text in case it was modified by Reputation Search
        const p = loader.querySelector('p');
        if (p) p.textContent = 'Выполняется парсинг, это может занять до минуты...';
        
        resultsContent.innerHTML = '';
        resultsContent.classList.add('hidden');
    };

    const handleError = (err) => {
        resultsContent.innerHTML = `<div class="status-badge status-error">Ошибка: ${err.message || err}</div>`;
        loader.classList.add('hidden');
        resultsContent.classList.remove('hidden');
    };

    // --- VISUAL RENDERERS ---

    const renderMod1 = (data) => {
        if (data.status !== 'success') throw new Error(data.error_message || 'Unknown error');
        return `
            <div class="rating-card">
                <div class="rating-value">${data.rating || 'N/A'} ⭐</div>
                <div class="rating-info">
                    <h3>Рейтинг Яндекс Карт</h3>
                    <p>Собрано на основе ${data.reviews_count || 0} оценок</p>
                </div>
            </div>
        `;
    };

    const renderMod2 = (data) => {
        if (data.status !== 'success') throw new Error(data.error_message || 'Unknown error');
        if (!data.new_reviews || data.new_reviews.length === 0) {
            return `<div class="status-badge status-success">Новых отзывов нет</div>`;
        }
        
        let html = `<h3>Собрано новых отзывов: ${data.new_reviews.length}</h3><div class="reviews-grid">`;
        data.new_reviews.forEach(r => {
            html += `
                <div class="review-card">
                    <div class="review-header">
                        <span>👤 ${r.author || 'Аноним'} ${r.has_reply ? '<span class="status-badge status-success" style="font-size: 0.7rem; padding: 2px 6px; margin-left: 5px;">Есть ответ</span>' : '<span class="status-badge status-error" style="font-size: 0.7rem; padding: 2px 6px; margin-left: 5px;">Нет ответа</span>'}</span>
                        <span class="review-rating">${r.rating ? r.rating + '★' : ''}</span>
                    </div>
                    <div class="review-date">${r.date_parsed || r.date_raw || ''}</div>
                    <div class="review-text">${r.text || ''}</div>
                </div>
            `;
        });
        html += `</div>`;
        return html;
    };

    const renderMod3 = (data) => {
        if (data.status !== 'success') throw new Error(data.error_message || 'Unknown error');
        if (!data.competitors || data.competitors.length === 0) {
            return `<div class="status-badge status-error">Конкуренты не найдены</div>`;
        }

        let html = `<div class="competitor-list">`;
        data.competitors.forEach(comp => {
            const adHtml = comp.is_ad 
                ? `<span class="status-badge ad-badge">Реклама: ${comp.ad_type || 'Да'}</span>` 
                : `<span class="status-badge status-success">Органика</span>`;

            const renderReview = (r, type) => `
                <div class="review-card review-type-${type === 'positive' ? 'pos' : 'neg'}">
                    <div class="review-header">
                        ${r.has_reply ? '<span class="status-badge status-success" style="font-size: 0.7rem; padding: 2px 6px;">Есть ответ</span>' : '<span class="status-badge status-error" style="font-size: 0.7rem; padding: 2px 6px;">Нет ответа</span>'}
                        <span class="review-rating">${r.rating}★</span>
                    </div>
                    <div class="review-text">${r.text}</div>
                </div>
            `;

            let posHtml = comp.top_positive_reviews.map(r => renderReview(r, 'positive')).join('');
            let negHtml = comp.top_negative_reviews.map(r => renderReview(r, 'negative')).join('');

            if (!posHtml) posHtml = `<p style="color:var(--text-muted);font-size:0.9rem;">Нет выраженных позитивных отзывов</p>`;
            if (!negHtml) negHtml = `<p style="color:var(--text-muted);font-size:0.9rem;">Нет выраженных негативных отзывов</p>`;

            html += `
                <div class="competitor-card">
                    <div class="comp-header">
                        <div class="comp-title">
                            <h3>${comp.name || 'Неизвестно'}</h3>
                            ${adHtml}
                            ${comp.url ? `<a href="${comp.url}" target="_blank">Ссылка ↗</a>` : ''}
                        </div>
                        <div class="comp-stats">
                            <span>⭐ ${comp.rating || 'N/A'}</span>
                            <span>📝 ${comp.reviews_count || 0} оценок</span>
                        </div>
                    </div>
                    <div class="comp-reviews-section">
                        <div class="review-col">
                            <h4>Плюсы (Топ позитив)</h4>
                            <div class="reviews-grid" style="grid-template-columns:1fr; margin-top:0;">
                                ${posHtml}
                            </div>
                        </div>
                        <div class="review-col">
                            <h4>Минусы (Топ негатив)</h4>
                            <div class="reviews-grid" style="grid-template-columns:1fr; margin-top:0;">
                                ${negHtml}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
        return html;
    };

    // Generic API call handler
    const apiCall = async (endpoint, body, renderFunc) => {
        try {
            showLoading();
            const res = await fetch(`/api/v1/parse/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            const data = await res.json();
            
            const html = renderFunc(data);
            resultsContent.innerHTML = html;
        } catch (err) {
            handleError(err);
        } finally {
            loader.classList.add('hidden');
            resultsContent.classList.remove('hidden');
        }
    };

    // Event Listeners
    document.getElementById('form-mod1').addEventListener('submit', (e) => {
        e.preventDefault();
        const platform = document.getElementById('mod1-platform').value;
        const endpoint = platform === 'twogis' ? 'twogis-map' : 'yandex-map';
        apiCall(endpoint, { url: document.getElementById('mod1-url').value }, renderMod1);
    });

    document.getElementById('form-mod2').addEventListener('submit', (e) => {
        e.preventDefault();
        const platform = document.getElementById('mod2-platform').value;
        const endpoint = platform === 'twogis' ? 'twogis-reviews-monitor' : 'reviews-monitor';
        let dateVal = new Date(document.getElementById('mod2-date').value).toISOString();
        apiCall(endpoint, { 
            url: document.getElementById('mod2-url').value,
            last_check_date: dateVal
        }, renderMod2);
    });

    document.getElementById('form-mod3').addEventListener('submit', (e) => {
        e.preventDefault();
        const platform = document.getElementById('mod3-platform').value;
        const endpoint = platform === 'twogis' ? 'twogis-competitors' : 'competitors';
        apiCall(endpoint, {
            url: document.getElementById('mod3-url').value,
            radius: parseInt(document.getElementById('mod3-radius').value),
            query: document.getElementById('mod3-query').value,
            limit: parseInt(document.getElementById('mod3-limit').value)
        }, renderMod3);
    });

    // --- MODULE 4 LOGIC ---
    window.currentReputationSites = [];
    let reputationChartInstance = null;

    const renderMod4 = (data) => {
        if (data.status === 'error') {
            return `<div class="error-msg">Ошибка: ${data.error_message || 'Неизвестная ошибка'}</div>`;
        }
        
        window.currentReputationData = {
            website_title: data.website_title || "Компания",
            search_query: data.search_query || ""
        };
        window.currentReputationSites = JSON.parse(JSON.stringify(data.sites || [])); // clone

        let html = `
            <h2>Результаты поиска репутации</h2>
            <div style="margin-bottom: 1rem;">
                <strong>Компания:</strong> ${data.website_title}<br>
                <strong>Поисковый запрос:</strong> <code>${data.search_query}</code>
            </div>
            
            <div class="chart-container">
                <canvas id="reputationChart"></canvas>
            </div>

            <table class="results-table" style="width:100%; border-collapse: collapse; margin-top: 1rem;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--panel-border); text-align: left;">
                        <th style="padding: 0.5rem;">Площадка</th>
                        <th style="padding: 0.5rem;">Рейтинг</th>
                        <th style="padding: 0.5rem;">Оценок</th>
                        <th style="padding: 0.5rem;">Был рейтинг</th>
                        <th style="padding: 0.5rem;">Было оценок</th>
                        <th style="padding: 0.5rem;">Скриншот</th>
                        <th style="padding: 0.5rem; text-align: center;">Действия</th>
                    </tr>
                </thead>
                <tbody>
        `;

        if (!data.sites || data.sites.length === 0) {
            html += `<tr><td colspan="6" style="padding: 1rem; text-align: center;">Площадки не найдены</td></tr>`;
        } else {
            data.sites.forEach(site => {
                let isIrrelevant = site.status && site.status.includes('irrelevant');
                let statusIcon = site.status === 'success' ? '✅' : (isIrrelevant ? '🚫' : '⚠️');
                let statusTooltip = site.status === 'success' ? 'Рейтинг успешно найден' : 'Рейтинг не найден в стандартном коде (возможно, сайт блокирует запросы или скрывает рейтинг скриптами)';
                if (site.status.includes('error')) {
                    statusTooltip = 'Ошибка при попытке открыть сайт: ' + site.status;
                } else if (isIrrelevant) {
                    statusTooltip = 'Страница отсеяна как нерелевантная (другая компания или город): ' + site.status;
                }
                
                let rating = '';
                if (site.rating) {
                    rating = `⭐ ${site.rating}`;
                } else if (!isIrrelevant) {
                    rating = `
                        <div class="manual-rating-wrapper">
                            <input type="number" step="0.1" min="1" max="5" class="manual-rating-input" data-domain="${site.domain}" placeholder="-">
                            <button class="manual-rating-btn" onclick="window.addManualRating('${site.domain}', this)">+</button>
                        </div>
                    `;
                } else {
                    rating = '<span style="color:var(--text-muted)">Отсеян</span>';
                }

                let count = site.reviews_count ? site.reviews_count : '<span style="color:var(--text-muted)">—</span>';
                
                if (isIrrelevant) {
                    count = '<span style="color:var(--text-muted)">Отсеян</span>';
                }
                
                let ratingChangeHtml = '';
                if (site.rating_change !== null && site.rating_change !== undefined) {
                    let color = site.rating_change > 0 ? 'var(--success)' : (site.rating_change < 0 ? 'var(--error)' : 'var(--text-muted)');
                    let sign = site.rating_change > 0 ? '+' : '';
                    ratingChangeHtml = ` <span style="color:${color}; font-size: 0.8em;">(${sign}${site.rating_change})</span>`;
                }

                let countChangeHtml = '';
                if (site.reviews_count_change !== null && site.reviews_count_change !== undefined) {
                    let color = site.reviews_count_change > 0 ? 'var(--success)' : (site.reviews_count_change < 0 ? 'var(--error)' : 'var(--text-muted)');
                    let sign = site.reviews_count_change > 0 ? '+' : '';
                    countChangeHtml = ` <span style="color:${color}; font-size: 0.8em;">(${sign}${site.reviews_count_change})</span>`;
                }

                let prevRating = site.previous_rating !== null && site.previous_rating !== undefined ? site.previous_rating : '<span style="color:var(--text-muted)">—</span>';
                let prevCount = site.previous_reviews_count !== null && site.previous_reviews_count !== undefined ? site.previous_reviews_count : '<span style="color:var(--text-muted)">—</span>';
                
                let screenshotLink = site.screenshot_url ? `<a href="${site.screenshot_url}" target="_blank" style="color:var(--primary-color);">📷 Скриншот</a>` : '<span style="color:var(--text-muted)">—</span>';

                html += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 0.5rem;" title="${statusTooltip}">
                            ${statusIcon} <a href="${site.url}" target="_blank" style="color: var(--primary-color); text-decoration: none;">${site.domain}</a>
                        </td>
                        <td style="padding: 0.5rem;">${rating}${ratingChangeHtml}</td>
                        <td style="padding: 0.5rem;">${count}${countChangeHtml}</td>
                        <td style="padding: 0.5rem;">${prevRating}</td>
                        <td style="padding: 0.5rem;">${prevCount}</td>
                        <td style="padding: 0.5rem;">${screenshotLink}</td>
                        <td style="padding: 0.5rem; text-align: center;">
                            <button class="action-btn delete-btn" onclick="window.deleteReputationSite('${site.domain}')" title="Удалить" style="background: var(--error); color: white; border: none; padding: 0.3rem 0.6rem; border-radius: 4px; cursor: pointer;">🗑️</button>
                        </td>
                    </tr>
                `;
            });
        }
        
        html += `
                <tr style="border-top: 2px solid rgba(255,255,255,0.1); background: rgba(0,0,0,0.2);">
                    <td style="padding: 0.5rem;"><input type="text" id="new-site-domain" placeholder="Домен (yandex.ru)" style="width:100%;" class="input-field"></td>
                    <td style="padding: 0.5rem;"><input type="number" id="new-site-rating" placeholder="Рейтинг (1-5)" step="0.1" min="1" max="5" style="width:100%;" class="input-field"></td>
                    <td style="padding: 0.5rem;"><input type="number" id="new-site-count" placeholder="Кол-во отзывов" min="0" style="width:100%;" class="input-field"></td>
                    <td style="padding: 0.5rem;" colspan="3"><input type="text" id="new-site-url" placeholder="Ссылка (https://...)" style="width:100%;" class="input-field"></td>
                    <td style="padding: 0.5rem; text-align: center;">
                        <button class="action-btn" onclick="window.addReputationSite()" style="background: var(--primary-color); color: white; border: none; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer;">Добавить</button>
                    </td>
                </tr>
            </tbody></table>`;
        return html;
    };

    window.updateReputationChart = () => {
        if (!window.currentReputationSites || window.currentReputationSites.length === 0) return;
        
        const canvas = document.getElementById('reputationChart');
        if (!canvas) return;

        let positive = 0;
        let neutral = 0;
        let negative = 0;
        let posSites = [];
        let neuSites = [];
        let negSites = [];

        window.currentReputationSites.forEach(site => {
            if (site.status && site.status.includes('irrelevant')) return;
            if (!site.rating) return;
            
            const r = parseFloat(site.rating);
            if (isNaN(r)) return;

            if (r >= 4.5) {
                positive++;
                posSites.push(site.domain);
            } else if (r >= 4.0) {
                neutral++;
                neuSites.push(site.domain);
            } else {
                negative++;
                negSites.push(site.domain);
            }
        });

        // Hide chart container if no ratings at all
        const container = canvas.parentElement;
        if (positive === 0 && neutral === 0 && negative === 0) {
            container.style.display = 'none';
            return;
        } else {
            container.style.display = 'block';
        }

        const data = {
            labels: ['Позитивные (>= 4.5)', 'Нейтральные (4.0 - 4.49)', 'Негативные (< 4.0)'],
            datasets: [{
                data: [positive, neutral, negative],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.8)', // Success
                    'rgba(245, 158, 11, 0.8)', // Warning
                    'rgba(239, 68, 68, 0.8)'   // Error
                ],
                borderColor: [
                    'rgba(16, 185, 129, 1)',
                    'rgba(245, 158, 11, 1)',
                    'rgba(239, 68, 68, 1)'
                ],
                borderWidth: 1,
                hoverOffset: 4
            }]
        };

        if (reputationChartInstance) {
            reputationChartInstance.destroy();
        }

        reputationChartInstance = new Chart(canvas, {
            type: 'doughnut',
            data: data,
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#e2e8f0' }
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const index = context.dataIndex;
                                if (index === 0) return posSites.length ? ['Сайты:'].concat(posSites) : '';
                                if (index === 1) return neuSites.length ? ['Сайты:'].concat(neuSites) : '';
                                if (index === 2) return negSites.length ? ['Сайты:'].concat(negSites) : '';
                                return '';
                            }
                        }
                    }
                }
            }
        });
    };

    window.saveReputationHistory = async () => {
        if (!window.currentReputationHistoryId) return;
        try {
            await fetch(`/api/v1/reputation/history/${window.currentReputationHistoryId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: "success",
                    website_title: window.currentReputationData?.website_title || "Компания",
                    search_query: window.currentReputationData?.search_query || "",
                    sites: window.currentReputationSites,
                    history_id: window.currentReputationHistoryId
                })
            });
        } catch(e) {
            console.error("Ошибка сохранения в историю:", e);
        }
    };

    window.addManualRating = async (domain, btnElement) => {
        const input = btnElement.previousElementSibling;
        const val = parseFloat(input.value);
        if (isNaN(val) || val < 1 || val > 5) {
            alert('Введите корректную оценку от 1 до 5');
            return;
        }

        const site = window.currentReputationSites.find(s => s.domain === domain);
        if (site) {
            site.rating = val;
            
            const wrapper = btnElement.parentElement;
            wrapper.outerHTML = `⭐ ${val} <span style="font-size:0.7em; color:var(--text-muted)">(ручн.)</span>`;
            
            window.updateReputationChart();
            await window.saveReputationHistory();
        }
    };

    window.deleteReputationSite = async (domain) => {
        if (!confirm(`Удалить площадку ${domain}?`)) return;
        window.currentReputationSites = window.currentReputationSites.filter(s => s.domain !== domain);
        
        // Re-render
        if (window.currentReputationData) {
            window.currentReputationData.sites = window.currentReputationSites;
            document.getElementById('results-content').innerHTML = renderMod4(window.currentReputationData);
            window.updateReputationChart();
        }
        
        await window.saveReputationHistory();
    };

    window.addReputationSite = async () => {
        const domain = document.getElementById('new-site-domain').value.trim();
        const url = document.getElementById('new-site-url').value.trim();
        const rating = parseFloat(document.getElementById('new-site-rating').value);
        const count = parseInt(document.getElementById('new-site-count').value);

        if (!domain) {
            alert('Введите домен');
            return;
        }

        const newSite = {
            domain: domain,
            url: url || `https://${domain}`,
            rating: isNaN(rating) ? null : rating,
            reviews_count: isNaN(count) ? null : count,
            status: 'success'
        };

        window.currentReputationSites.push(newSite);

        if (window.currentReputationData) {
            window.currentReputationData.sites = window.currentReputationSites;
            document.getElementById('results-content').innerHTML = renderMod4(window.currentReputationData);
            window.updateReputationChart();
        }

        await window.saveReputationHistory();
    };

    // --- MODULE 4 PROJECTS LOGIC ---
    let mod4ProjectsList = [];
    const mod4ProjectSelect = document.getElementById('mod4-project');
    const mod4ProjectNameGroup = document.getElementById('mod4-project-name-group');
    const mod4ProjectNameInput = document.getElementById('mod4-project-name');
    
    const mod4Company = document.getElementById('mod4-company');
    const mod4Direction = document.getElementById('mod4-direction');
    const mod4City = document.getElementById('mod4-city');
    const mod4Address = document.getElementById('mod4-address');
    const mod4Website = document.getElementById('mod4-website');

    if (mod4ProjectSelect) {
        const loadMod4Projects = async () => {
            try {
                const res = await fetch('/api/v1/projects');
                mod4ProjectsList = await res.json();
                
                Array.from(mod4ProjectSelect.options).forEach(opt => {
                    if(opt.value !== 'new') opt.remove();
                });
                
                mod4ProjectsList.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    opt.textContent = p.name;
                    mod4ProjectSelect.appendChild(opt);
                });
            } catch (e) {
                console.error('Failed to load projects for mod4', e);
            }
        };
        
        // Initial load
        loadMod4Projects();
        
        mod4ProjectSelect.addEventListener('change', (e) => {
            if (e.target.value === 'new') {
                mod4ProjectNameGroup.style.display = 'flex';
                mod4ProjectNameInput.required = true;
                
                mod4Company.value = '';
                mod4Direction.value = '';
                mod4City.value = '';
                mod4Address.value = '';
                if (mod4Website) mod4Website.value = '';
            } else {
                mod4ProjectNameGroup.style.display = 'none';
                mod4ProjectNameInput.required = false;
                
                const p = mod4ProjectsList.find(x => x.id === e.target.value);
                if (p) {
                    mod4Company.value = p.company || '';
                    mod4Direction.value = p.direction || '';
                    mod4City.value = p.city || '';
                    mod4Address.value = p.address || '';
                    if (mod4Website) mod4Website.value = p.website || '';
                }
            }
        });
    }

    document.getElementById('form-mod4').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            showLoading();
            
            // Находим элемент с текстом статуса внутри лоадера
            let loadingText = loader.querySelector('p');
            if (!loadingText) {
                loadingText = document.createElement('p');
                loadingText.style.marginTop = '1rem';
                loadingText.style.color = 'var(--text-muted)';
                loader.appendChild(loadingText);
            }
            loadingText.textContent = "Подготовка...";

            const payload = {
                company: mod4Company.value,
                direction: mod4Direction.value,
                city: mod4City.value,
                address: mod4Address.value,
                website: mod4Website ? mod4Website.value : undefined
            };

            if (mod4ProjectSelect && mod4ProjectSelect.value === 'new') {
                try {
                    const newProjPayload = {
                        name: mod4ProjectNameInput.value,
                        links: [],
                        company: payload.company,
                        direction: payload.direction,
                        city: payload.city,
                        address: payload.address,
                        website: payload.website
                    };
                    const projRes = await fetch('/api/v1/projects', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(newProjPayload)
                    });
                    if(projRes.ok) {
                        const savedProj = await projRes.json();
                        const opt = document.createElement('option');
                        opt.value = savedProj.id;
                        opt.textContent = savedProj.name;
                        mod4ProjectSelect.appendChild(opt);
                        mod4ProjectSelect.value = savedProj.id;
                        mod4ProjectNameGroup.style.display = 'none';
                        mod4ProjectNameInput.required = false;
                        if(typeof fetchProjects === 'function') fetchProjects(); // refresh sidebar
                    }
                } catch(e) {
                    console.error("Error creating project", e);
                }
            }
            
            const res = await fetch(`/api/v1/reputation/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const reader = res.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                let lines = buffer.split('\n');
                buffer = lines.pop(); // Последняя часть может быть неполной
                
                for (let line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const parsed = JSON.parse(line);
                        if (parsed.type === "progress") {
                            loadingText.textContent = parsed.message;
                        } else if (parsed.type === "result") {
                            if (parsed.data.history_id) window.currentReputationHistoryId = parsed.data.history_id;
                            resultsContent.innerHTML = renderMod4(parsed.data);
                            window.updateReputationChart();
                        }
                    } catch (err) {
                        console.error("Error parsing stream line:", err, line);
                    }
                }
            }
            
            if (buffer.trim()) {
                try {
                    const parsed = JSON.parse(buffer);
                    if (parsed.type === "progress") {
                        loadingText.textContent = parsed.message;
                    } else if (parsed.type === "result") {
                        if (parsed.data.history_id) window.currentReputationHistoryId = parsed.data.history_id;
                        resultsContent.innerHTML = renderMod4(parsed.data);
                        window.updateReputationChart();
                    }
                } catch(e) {}
            }
            
        } catch (err) {
            handleError(err);
        } finally {
            loader.classList.add('hidden');
            resultsContent.classList.remove('hidden');
        }
    });

    // --- MODULE HISTORY LOGIC ---
    const btnLoadHistory = document.getElementById('btn-load-history');
    const historyList = document.getElementById('history-list');

    window.fetchHistory = async () => {
        try {
            historyList.innerHTML = '<div class="loader"><div class="spinner"></div><p>Загрузка истории...</p></div>';
            const res = await fetch('/api/v1/reputation/history');
            const data = await res.json();
            
            if (!data || data.length === 0) {
                historyList.innerHTML = '<p class="empty-state">История пуста.</p>';
                return;
            }
            
            let html = '';
            data.forEach(item => {
                const date = new Date(item.timestamp).toLocaleString();
                html += `
                    <div class="history-item glass-panel">
                        <div class="history-info">
                            <div style="display: flex; align-items: center;">
                                <span class="history-company">${item.company || 'Компания'}</span>
                                <span class="history-query">${item.query || ''}</span>
                            </div>
                            <div class="history-date">🕒 ${date}</div>
                        </div>
                        <div style="display: flex; gap: 0.5rem;">
                            <button class="primary-btn btn-view-history" data-id="${item.id}" style="margin: 0; padding: 0.5rem 1.25rem;">Открыть отчет</button>
                            <button class="btn-remove-link btn-delete-history" data-id="${item.id}" style="font-size: 1.25rem; width: 2.5rem; height: 2.5rem; display: flex; align-items: center; justify-content: center; background: rgba(239, 68, 68, 0.1); border-radius: 8px; color: var(--error); border: 1px solid rgba(239, 68, 68, 0.2); cursor: pointer;" title="Удалить">&times;</button>
                        </div>
                    </div>
                `;
            });
            historyList.innerHTML = html;
            
            document.querySelectorAll('.btn-view-history').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.target.getAttribute('data-id');
                    const item = data.find(x => x.id === id);
                    if (item && item.result) {
                        window.currentReputationHistoryId = id;
                        resultsContainer.classList.remove('hidden');
                        resultsContent.classList.remove('hidden');
                        loader.classList.add('hidden');
                        resultsContent.innerHTML = renderMod4(item.result);
                        window.updateReputationChart();
                    }
                });
            });

            document.querySelectorAll('.btn-delete-history').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    if (!confirm('Вы уверены, что хотите удалить этот отчет?')) return;
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/v1/reputation/history/${id}`, { method: 'DELETE' });
                        if (res.ok) {
                            fetchHistory(); // Перезагружаем список
                        } else {
                            alert('Ошибка при удалении отчета');
                        }
                    } catch (err) {
                        alert('Ошибка при удалении отчета: ' + err.message);
                    }
                });
            });
        } catch (err) {
            historyList.innerHTML = `<p class="error-msg">Ошибка загрузки: ${err.message}</p>`;
        }
    };

    if (btnLoadHistory) {
        btnLoadHistory.addEventListener('click', fetchHistory);
    }

    // --- MODULE COMPETITOR HISTORY LOGIC ---
    const btnLoadCompetitorHistory = document.getElementById('btn-load-competitor-history');
    const competitorHistoryList = document.getElementById('competitor-history-list');

    window.fetchCompetitorHistory = async () => {
        try {
            competitorHistoryList.innerHTML = '<div class="loader"><div class="spinner"></div><p>Загрузка истории...</p></div>';
            const res = await fetch('/api/v1/competitors/history');
            const data = await res.json();
            
            if (!data || data.length === 0) {
                competitorHistoryList.innerHTML = '<p class="empty-state">История пуста.</p>';
                return;
            }
            
            let html = '';
            data.forEach(item => {
                const date = new Date(item.timestamp).toLocaleString();
                html += `
                    <div class="history-item glass-panel">
                        <div class="history-info">
                            <div style="display: flex; align-items: center;">
                                <span class="history-company">${item.query || 'Без названия'}</span>
                            </div>
                            <div class="history-date">🕒 ${date}</div>
                        </div>
                        <div style="display: flex; gap: 0.5rem;">
                            <button class="primary-btn btn-view-competitor-history" data-id="${item.id}" style="margin: 0; padding: 0.5rem 1.25rem;">Открыть отчет</button>
                            <button class="btn-remove-link btn-delete-competitor-history" data-id="${item.id}" style="font-size: 1.25rem; width: 2.5rem; height: 2.5rem; display: flex; align-items: center; justify-content: center; background: rgba(239, 68, 68, 0.1); border-radius: 8px; color: var(--error); border: 1px solid rgba(239, 68, 68, 0.2); cursor: pointer;" title="Удалить">&times;</button>
                        </div>
                    </div>
                `;
            });
            competitorHistoryList.innerHTML = html;
            
            document.querySelectorAll('.btn-view-competitor-history').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.target.getAttribute('data-id');
                    const item = data.find(x => x.id === id);
                    if (item && item.result) {
                        resultsContainer.classList.remove('hidden');
                        resultsContent.classList.remove('hidden');
                        loader.classList.add('hidden');
                        resultsContent.innerHTML = renderMod3(item.result);
                    }
                });
            });

            document.querySelectorAll('.btn-delete-competitor-history').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    if (!confirm('Вы уверены, что хотите удалить этот анализ?')) return;
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/v1/competitors/history/${id}`, { method: 'DELETE' });
                        if (res.ok) {
                            fetchCompetitorHistory(); // Перезагружаем список
                        } else {
                            alert('Ошибка при удалении отчета');
                        }
                    } catch (err) {
                        alert('Ошибка при удалении отчета: ' + err.message);
                    }
                });
            });
        } catch (err) {
            competitorHistoryList.innerHTML = `<p class="error-msg">Ошибка загрузки: ${err.message}</p>`;
        }
    };

    if (btnLoadCompetitorHistory) {
        btnLoadCompetitorHistory.addEventListener('click', fetchCompetitorHistory);
    }

    // --- MODULE MENTIONS LOGIC ---
    const renderMentions = (data) => {
        if (data.status === 'error') {
            return `<div class="error-msg">Ошибка: ${data.error_message || 'Неизвестная ошибка'}</div>`;
        }

        let html = `
            <h2>Результаты поиска упоминаний</h2>
            <div style="margin-bottom: 1rem;">
                <strong>Компания:</strong> ${data.website_title || data.company || ''}<br>
                <strong>Поисковый запрос:</strong> <code>${data.search_query || ''}</code>
            </div>
            <table class="results-table" style="width:100%; border-collapse: collapse; margin-top: 1rem;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--panel-border); text-align: left;">
                        <th style="padding: 0.5rem;">Площадка</th>
                        <th style="padding: 0.5rem;">Упоминание найдено</th>
                        <th style="padding: 0.5rem;">Статус</th>
                    </tr>
                </thead>
                <tbody>
        `;

        if (!data.sites || data.sites.length === 0) {
            html += `<tr><td colspan="3" style="padding: 1rem; text-align: center;">Площадки не найдены</td></tr>`;
        } else {
            data.sites.forEach(site => {
                let statusIcon = site.status === 'success' ? '✅' : '⚠️';
                let mentionStatus = site.is_link_present ? '<span style="color:var(--success);">Да</span>' : '<span style="color:var(--error);">Нет</span>';
                
                if (site.status && site.status.includes('error')) {
                    statusIcon = '🚫';
                    mentionStatus = '<span style="color:var(--text-muted)">Ошибка загрузки</span>';
                }

                html += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 0.5rem;">
                            ${statusIcon} <a href="${site.url}" target="_blank" style="color: var(--accent); text-decoration: none;">${site.domain}</a>
                        </td>
                        <td style="padding: 0.5rem;">${mentionStatus}</td>
                        <td style="padding: 0.5rem;">${site.status === 'success' ? 'Проверено' : site.status}</td>
                    </tr>
                `;
            });
        }
        
        html += `</tbody></table>`;
        return html;
    };

    const formMentions = document.getElementById('form-mentions');
    if (formMentions) {
        formMentions.addEventListener('submit', async (e) => {
            e.preventDefault();
            try {
                showLoading();
                
                let loadingText = loader.querySelector('p');
                if (!loadingText) {
                    loadingText = document.createElement('p');
                    loadingText.style.marginTop = '1rem';
                    loadingText.style.color = 'var(--text-muted)';
                    loader.appendChild(loadingText);
                }
                loadingText.textContent = "Подготовка...";

                const payload = {
                    company: document.getElementById('mentions-company').value,
                    website: document.getElementById('mentions-website').value,
                    city: document.getElementById('mentions-city').value
                };
                
                const res = await fetch(`/api/v1/mentions/search`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const reader = res.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, { stream: true });
                    let lines = buffer.split('\n');
                    buffer = lines.pop();
                    
                    for (let line of lines) {
                        if (!line.trim()) continue;
                        try {
                            const parsed = JSON.parse(line);
                            if (parsed.type === "progress") {
                                loadingText.textContent = parsed.message;
                            } else if (parsed.type === "result") {
                                resultsContent.innerHTML = renderMentions(parsed.data);
                            }
                        } catch (err) {
                            console.error("Error parsing stream line:", err, line);
                        }
                    }
                }
                
                if (buffer.trim()) {
                    try {
                        const parsed = JSON.parse(buffer);
                        if (parsed.type === "progress") {
                            loadingText.textContent = parsed.message;
                        } else if (parsed.type === "result") {
                            resultsContent.innerHTML = renderMentions(parsed.data);
                        }
                    } catch(e) {}
                }
                
            } catch (err) {
                handleError(err);
            } finally {
                loader.classList.add('hidden');
                resultsContent.classList.remove('hidden');
            }
        });
    }

    // Mentions History
    const btnLoadMentionsHistory = document.getElementById('btn-load-mentions-history');
    const mentionsHistoryList = document.getElementById('mentions-history-list');

    window.fetchMentionsHistory = async () => {
        try {
            if (!mentionsHistoryList) return;
            mentionsHistoryList.innerHTML = '<div class="loader"><div class="spinner"></div><p>Загрузка истории...</p></div>';
            const res = await fetch('/api/v1/mentions/history');
            const data = await res.json();
            
            if (!data || data.length === 0) {
                mentionsHistoryList.innerHTML = '<p class="empty-state">История пуста.</p>';
                return;
            }
            
            let html = '';
            data.forEach(item => {
                const date = new Date(item.timestamp).toLocaleString();
                html += `
                    <div class="history-item glass-panel">
                        <div class="history-info">
                            <div style="display: flex; align-items: center;">
                                <span class="history-company">${item.company || 'Компания'}</span>
                                <span class="history-query">${item.query || ''}</span>
                            </div>
                            <div class="history-date">🕒 ${date}</div>
                        </div>
                        <div style="display: flex; gap: 0.5rem;">
                            <button class="primary-btn btn-view-mentions-history" data-id="${item.id}" style="margin: 0; padding: 0.5rem 1.25rem;">Открыть отчет</button>
                            <button class="btn-remove-link btn-delete-mentions-history" data-id="${item.id}" style="font-size: 1.25rem; width: 2.5rem; height: 2.5rem; display: flex; align-items: center; justify-content: center; background: rgba(239, 68, 68, 0.1); border-radius: 8px; color: var(--error); border: 1px solid rgba(239, 68, 68, 0.2); cursor: pointer;" title="Удалить">&times;</button>
                        </div>
                    </div>
                `;
            });
            mentionsHistoryList.innerHTML = html;
            
            document.querySelectorAll('.btn-view-mentions-history').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.target.getAttribute('data-id');
                    const item = data.find(x => x.id === id);
                    if (item && item.result) {
                        resultsContainer.classList.remove('hidden');
                        resultsContent.classList.remove('hidden');
                        loader.classList.add('hidden');
                        resultsContent.innerHTML = renderMentions(item.result);
                    }
                });
            });

            document.querySelectorAll('.btn-delete-mentions-history').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    if (!confirm('Вы уверены, что хотите удалить этот отчет?')) return;
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/v1/mentions/history/${id}`, { method: 'DELETE' });
                        if (res.ok) {
                            fetchMentionsHistory();
                        } else {
                            const err = await res.json();
                            alert('Ошибка при удалении отчета: ' + err.detail);
                        }
                    } catch (err) {
                        alert('Ошибка при удалении отчета: ' + err.message);
                    }
                });
            });
        } catch (err) {
            if(mentionsHistoryList) mentionsHistoryList.innerHTML = `<p class="error-msg">Ошибка загрузки: ${err.message}</p>`;
        }
    };

    if (btnLoadMentionsHistory) {
        btnLoadMentionsHistory.addEventListener('click', fetchMentionsHistory);
    }

    // --- MODULE NEGATIVE LOGIC ---
    window.currentNegativeSites = [];
    window.currentNegativeHistoryId = null;

    const renderNegative = (data) => {
        if (data.status === 'error') {
            return `<div class="error-msg">Ошибка: ${data.error_message || 'Неизвестная ошибка'}</div>`;
        }
        
        window.currentNegativeSites = JSON.parse(JSON.stringify(data.sites || []));
        window.currentNegativeHistoryId = data.history_id || window.currentNegativeHistoryId;

        let html = `
            <h2>Результаты поиска негатива</h2>
            <div style="margin-bottom: 1rem;">
                <strong>Запрос:</strong> <code>${data.search_query}</code>
            </div>
            
            <table class="results-table" style="width:100%; border-collapse: collapse; margin-top: 1rem;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--panel-border); text-align: left;">
                        <th style="padding: 0.5rem;">Площадка</th>
                        <th style="padding: 0.5rem;">Негативных оценок</th>
                    </tr>
                </thead>
                <tbody>
        `;

        if (!data.sites || data.sites.length === 0) {
            html += `<tr><td colspan="2" style="padding: 1rem; text-align: center;">Площадки не найдены</td></tr>`;
        } else {
            data.sites.forEach(site => {
                let statusIcon = site.status === 'success' ? '✅' : '⚠️';
                let statusTooltip = site.status === 'success' ? 'Парсинг успешен' : site.status;
                
                let countHtml = '';
                if (site.negative_count !== null && site.negative_count !== undefined) {
                    countHtml = `<span style="font-weight: 600; color: ${site.negative_count > 0 ? 'var(--error)' : 'var(--success)'};">${site.negative_count}</span>`;
                } else {
                    countHtml = '<span style="color:var(--text-muted)">—</span>';
                }

                html += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 0.5rem;" title="${statusTooltip}">
                            ${statusIcon} <a href="${site.url}" target="_blank" style="color: var(--primary-color); text-decoration: none;">${site.domain}</a>
                        </td>
                        <td style="padding: 0.5rem;">${countHtml}</td>
                    </tr>
                `;
            });
        }
        
        html += `</tbody></table>`;
        return html;
    };

    const formNegative = document.getElementById('form-negative');
    if (formNegative) {
        formNegative.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const rawQueries = document.getElementById('negative-query').value;
            const queries = rawQueries.split('\n').map(q => q.trim()).filter(q => q.length > 0);
            
            if (queries.length === 0) {
                alert("Введите хотя бы один запрос");
                return;
            }
            
            const payload = { queries };

            loader.classList.remove('hidden');
            let loadingText = loader.querySelector('p');
            if (!loadingText) {
                loadingText = document.createElement('p');
                loadingText.style.marginTop = '1rem';
                loadingText.style.color = 'var(--text-muted)';
                loader.appendChild(loadingText);
            }
            loadingText.textContent = "Инициализация...";
            resultsContent.innerHTML = '';
            resultsContainer.classList.remove('hidden');
            resultsContent.classList.add('hidden');
            
            try {
                const response = await fetch('/api/v1/negative/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, { stream: true });
                    let lines = buffer.split('\n');
                    buffer = lines.pop();
                    
                    for (let line of lines) {
                        if (!line.trim()) continue;
                        try {
                            const parsed = JSON.parse(line);
                            if (parsed.type === "progress") {
                                loadingText.textContent = parsed.message;
                            } else if (parsed.type === "result") {
                                resultsContent.innerHTML = renderNegative(parsed.data);
                            }
                        } catch (err) {}
                    }
                }
                
                if (buffer.trim()) {
                    try {
                        const parsed = JSON.parse(buffer);
                        if (parsed.type === "progress") {
                            loadingText.textContent = parsed.message;
                        } else if (parsed.type === "result") {
                            resultsContent.innerHTML = renderNegative(parsed.data);
                        }
                    } catch(e) {}
                }
                
            } catch (err) {
                handleError(err);
            } finally {
                loader.classList.add('hidden');
                resultsContent.classList.remove('hidden');
            }
        });
    }

    // Negative History
    const btnLoadNegativeHistory = document.getElementById('btn-load-negative-history');
    const negativeHistoryList = document.getElementById('negative-history-list');

    window.fetchNegativeHistory = async () => {
        try {
            if (!negativeHistoryList) return;
            negativeHistoryList.innerHTML = '<div class="loader"><div class="spinner"></div><p>Загрузка истории...</p></div>';
            const res = await fetch('/api/v1/negative/history');
            const data = await res.json();
            
            if (!data || data.length === 0) {
                negativeHistoryList.innerHTML = '<p class="empty-state">История пуста.</p>';
                return;
            }
            
            let html = '';
            data.forEach(item => {
                const date = new Date(item.timestamp).toLocaleString();
                html += `
                    <div class="history-item glass-panel">
                        <div class="history-info">
                            <div style="display: flex; align-items: center;">
                                <span class="history-query">${item.query || ''}</span>
                            </div>
                            <div class="history-date">🕒 ${date}</div>
                        </div>
                        <div style="display: flex; gap: 0.5rem;">
                            <button class="primary-btn btn-view-negative-history" data-id="${item.id}" style="margin: 0; padding: 0.5rem 1.25rem;">Открыть отчет</button>
                            <button class="btn-remove-link btn-delete-negative-history" data-id="${item.id}" style="font-size: 1.25rem; width: 2.5rem; height: 2.5rem; display: flex; align-items: center; justify-content: center; background: rgba(239, 68, 68, 0.1); border-radius: 8px; color: var(--error); border: 1px solid rgba(239, 68, 68, 0.2); cursor: pointer;" title="Удалить">&times;</button>
                        </div>
                    </div>
                `;
            });
            negativeHistoryList.innerHTML = html;
            
            document.querySelectorAll('.btn-view-negative-history').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.target.getAttribute('data-id');
                    const item = data.find(x => x.id === id);
                    if (item && item.result) {
                        window.currentNegativeHistoryId = id;
                        resultsContainer.classList.remove('hidden');
                        resultsContent.classList.remove('hidden');
                        loader.classList.add('hidden');
                        resultsContent.innerHTML = renderNegative(item.result);
                    }
                });
            });

            document.querySelectorAll('.btn-delete-negative-history').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    if (!confirm('Вы уверены, что хотите удалить этот отчет?')) return;
                    const id = e.target.getAttribute('data-id');
                    try {
                        const res = await fetch(`/api/v1/negative/history/${id}`, { method: 'DELETE' });
                        if (res.ok) {
                            fetchNegativeHistory();
                        } else {
                            const err = await res.json();
                            alert('Ошибка при удалении отчета: ' + err.detail);
                        }
                    } catch (err) {
                        alert('Ошибка при удалении отчета: ' + err.message);
                    }
                });
            });
        } catch (err) {
            if(negativeHistoryList) negativeHistoryList.innerHTML = `<p class="error-msg">Ошибка загрузки: ${err.message}</p>`;
        }
    };

    if (btnLoadNegativeHistory) {
        btnLoadNegativeHistory.addEventListener('click', fetchNegativeHistory);
    }

});
