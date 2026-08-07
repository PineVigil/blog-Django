/**
 * toflower blog · Editorial 主题 JS(原生,无依赖)
 * 功能:主题切换 / 3D 倾斜 / 磁吸按钮 / 视差 / 逐字动画 /
 *      数字计数 / 滚动揭示 / 阅读进度 / 返回顶部 / 移动端导航
 */
(function () {
    'use strict';

    /* ---------- 壁纸自适应: 从壁纸提取主色, 生成同色系文字/光标颜色 ---------- */
    function rgbToHsl(r, g, b) {
        r /= 255; g /= 255; b /= 255;
        var max = Math.max(r, g, b), min = Math.min(r, g, b);
        var h, s, l = (max + min) / 2;
        if (max === min) { h = 0; s = 0; }
        else {
            var dd = max - min;
            s = l > 0.5 ? dd / (2 - max - min) : dd / (max + min);
            switch (max) {
                case r: h = (g - b) / dd + (g < b ? 6 : 0); break;
                case g: h = (b - r) / dd + 2; break;
                default: h = (r - g) / dd + 4;
            }
            h *= 60;
        }
        return [h, s, l];
    }
    /* ---------- 手动顶栏配色: 指定背景色(可选文字色), 未指定文字色时按背景亮度自动取深/浅 ---------- */
    function hexToRgba(hex, alpha) {
        var r = parseInt(hex.slice(1, 3), 16);
        var g = parseInt(hex.slice(3, 5), 16);
        var b = parseInt(hex.slice(5, 7), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }
    function applyManualNav(bgHex, textHex) {
        if (!/^#[0-9a-fA-F]{6}$/.test(bgHex)) return;
        var root = document.documentElement;
        var r = parseInt(bgHex.slice(1, 3), 16);
        var g = parseInt(bgHex.slice(3, 5), 16);
        var b = parseInt(bgHex.slice(5, 7), 16);
        var lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        var hsl = rgbToHsl(r, g, b);
        var h = hsl[0], st = Math.max(0, Math.min(100, Math.round(hsl[1] * 100)));
        if (textHex && /^#[0-9a-fA-F]{6}$/.test(textHex)) {
            // 指定文字颜色: 顶栏文字固定用它, 未激活链接淡化到 70%
            root.style.setProperty('--nav-text', textHex);
            root.style.setProperty('--nav-mute', hexToRgba(textHex, 0.7));
        } else if (lum >= 0.5) {
            // 浅色顶栏 → 深色文字
            root.style.setProperty('--nav-text', 'hsl(' + h + ',' + Math.max(0, Math.round(st * .8)) + '%,15%)');
            root.style.setProperty('--nav-mute', 'hsl(' + h + ',' + Math.round(st * .7) + '%,38%)');
        } else {
            // 深色顶栏 → 浅色文字
            root.style.setProperty('--nav-text', 'hsl(' + h + ',' + Math.round(st * .5) + '%,92%)');
            root.style.setProperty('--nav-mute', 'hsl(' + h + ',' + Math.round(st * .45) + '%,68%)');
        }
        // 背景与控制按钮配色: 始终按背景色亮度生成
        if (lum >= 0.5) {
            root.style.setProperty('--nav-bg', bgHex);
            root.style.setProperty('--nav-border', 'hsla(' + h + ',' + Math.round(st * .4) + '%,84%,.9)');
            root.style.setProperty('--nav-ctrl-bg', 'hsla(' + h + ',' + Math.round(st * .3) + '%,94%,.9)');
            root.style.setProperty('--nav-ctrl-border', 'hsla(' + h + ',' + Math.round(st * .4) + '%,76%,.85)');
        } else {
            root.style.setProperty('--nav-bg', bgHex);
            root.style.setProperty('--nav-border', 'hsla(' + h + ',' + Math.round(st * .4) + '%,38%,.55)');
            root.style.setProperty('--nav-ctrl-bg', 'hsla(' + h + ',' + Math.round(st * .4) + '%,16%,.75)');
            root.style.setProperty('--nav-ctrl-border', 'hsla(' + h + ',' + Math.round(st * .4) + '%,42%,.5)');
        }
    }
    var navMode = document.body.getAttribute('data-nav-mode') || 'auto';
    var manualColor = document.body.getAttribute('data-nav-color') || '';
    var manualTextColor = document.body.getAttribute('data-nav-text') || '';
    var wpImg = document.querySelector('.hero-bg-image');
    if (wpImg) {
        document.documentElement.classList.add('wallpaper-set');
        var probe = new Image();
        probe.onload = function () {
            try {
                var s = 48, canvas = document.createElement('canvas');
                canvas.width = s; canvas.height = s;
                var ctx = canvas.getContext('2d');
                ctx.drawImage(probe, 0, 0, s, s);
                var d = ctx.getImageData(0, 0, s, s).data;
                var r = 0, g = 0, b = 0, n = d.length / 4;
                for (var i = 0; i < d.length; i += 4) { r += d[i]; g += d[i + 1]; b += d[i + 2]; }
                r = r / n; g = g / n; b = b / n;
                // 感知亮度加权
                var lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
                var hsl = rgbToHsl(r, g, b);
                var h = hsl[0], st = Math.min(100, Math.max(12, Math.round(hsl[1] * 100)));
                var root = document.documentElement;
                // 壁纸明暗标记: 深色壁纸下整体切深色表面+浅色文字, 保证正文可见
                root.setAttribute('data-wallpaper', lum < 0.5 ? 'dark' : 'light');
                if (lum >= 0.5) {
                    // 亮壁纸 → 同色系深色文字(保留壁纸色相, 压暗保证对比)
                    root.style.setProperty('--wp-title', 'hsl(' + h + ',' + st + '%,8%)');
                    root.style.setProperty('--wp-eyebrow', 'hsl(' + h + ',' + Math.round(st * .85) + '%,22%)');
                    root.style.setProperty('--wp-subtitle', 'hsl(' + h + ',' + Math.round(st * .9) + '%,13%)');
                    root.style.setProperty('--wp-meta', 'hsl(' + h + ',' + Math.round(st * .85) + '%,22%)');
                    root.style.setProperty('--wp-counter', 'hsl(' + h + ',' + Math.round(st * .9) + '%,13%)');
                    root.style.setProperty('--wp-ghost-border', 'hsla(' + h + ',' + st + '%,12%,.65)');
                    // 导航栏: 亮壁纸 → 深色文字 + 半透明浅色背景
                    root.style.setProperty('--nav-text', 'hsl(' + h + ',' + st + '%,15%)');
                    root.style.setProperty('--nav-mute', 'hsl(' + h + ',' + Math.round(st * .8) + '%,38%)');
                    root.style.setProperty('--nav-bg', 'hsla(' + h + ',' + Math.round(st * .45) + '%,97%,.88)');
                    root.style.setProperty('--nav-border', 'hsla(' + h + ',' + Math.round(st * .5) + '%,86%,.9)');
                    root.style.setProperty('--nav-ctrl-bg', 'hsla(' + h + ',' + Math.round(st * .45) + '%,95%,.9)');
                    root.style.setProperty('--nav-ctrl-border', 'hsla(' + h + ',' + Math.round(st * .5) + '%,80%,.85)');
                } else {
                    // 暗壁纸 → 同色系浅色文字(提亮保证对比)
                    root.style.setProperty('--wp-title', 'hsl(' + h + ',' + Math.round(st * .7) + '%,94%)');
                    root.style.setProperty('--wp-eyebrow', 'hsl(' + h + ',' + Math.round(st * .6) + '%,80%)');
                    root.style.setProperty('--wp-subtitle', 'hsl(' + h + ',' + Math.round(st * .7) + '%,90%)');
                    root.style.setProperty('--wp-meta', 'hsl(' + h + ',' + Math.round(st * .6) + '%,80%)');
                    root.style.setProperty('--wp-counter', 'hsl(' + h + ',' + Math.round(st * .7) + '%,90%)');
                    root.style.setProperty('--wp-ghost-border', 'hsla(' + h + ',' + Math.round(st * .7) + '%,90%,.55)');
                    // 导航栏: 暗壁纸 → 浅色文字 + 半透明深色背景
                    root.style.setProperty('--nav-text', 'hsl(' + h + ',' + Math.round(st * .55) + '%,92%)');
                    root.style.setProperty('--nav-mute', 'hsl(' + h + ',' + Math.round(st * .5) + '%,68%)');
                    root.style.setProperty('--nav-bg', 'hsla(' + h + ',' + Math.round(st * .5) + '%,10%,.88)');
                    root.style.setProperty('--nav-border', 'hsla(' + h + ',' + Math.round(st * .45) + '%,40%,.55)');
                    root.style.setProperty('--nav-ctrl-bg', 'hsla(' + h + ',' + Math.round(st * .5) + '%,18%,.75)');
                    root.style.setProperty('--nav-ctrl-border', 'hsla(' + h + ',' + Math.round(st * .45) + '%,45%,.5)');
                }
            } catch (e) { /* 跨域等异常时保持默认 */ }
            // 手动配色优先: 覆盖壁纸自动取色结果
            if (navMode === 'manual' && manualColor) applyManualNav(manualColor, manualTextColor);
        };
        probe.src = wpImg.src;
    } else if (navMode === 'manual' && manualColor) {
        applyManualNav(manualColor, manualTextColor);
    }

    /* ---------- 局部壁纸自适应: 正文文字颜色随所在位置的壁纸明暗实时变化 ---------- */
    if (wpImg) {
        var GRID_X = 24, GRID_Y = 16;
        var brightGrid = new Float32Array(GRID_X * GRID_Y);
        var gridReady = false;
        var adaptEls = [];

        // 把壁纸按 CSS object-fit: cover 的裁切画进小画布, 统计每格平均亮度
        function buildBrightnessGrid() {
            try {
                var s = 96;
                var c = document.createElement('canvas');
                c.width = s; c.height = s;
                var ctx = c.getContext('2d');
                var W = wpImg.naturalWidth, H = wpImg.naturalHeight;
                if (!W || !H) return;
                var sc = Math.max(s / W, s / H);
                var dw = W * sc, dh = H * sc;
                ctx.drawImage(wpImg, (s - dw) / 2, (s - dh) / 2, dw, dh);
                var d = ctx.getImageData(0, 0, s, s).data;
                for (var j = 0; j < GRID_Y; j++) {
                    var y0 = Math.floor(j * s / GRID_Y), y1 = Math.floor((j + 1) * s / GRID_Y);
                    for (var i = 0; i < GRID_X; i++) {
                        var x0 = Math.floor(i * s / GRID_X), x1 = Math.floor((i + 1) * s / GRID_X);
                        var sum = 0, n = 0;
                        for (var y = y0; y < y1; y++) {
                            for (var x = x0; x < x1; x++) {
                                var p = (y * s + x) * 4;
                                sum += 0.299 * d[p] + 0.587 * d[p + 1] + 0.114 * d[p + 2];
                                n++;
                            }
                        }
                        brightGrid[j * GRID_X + i] = n ? sum / n / 255 : 0.5;
                    }
                }
                gridReady = true;
            } catch (e) { gridReady = false; }
        }

        // 视口坐标 → 壁纸网格坐标(与 object-fit: cover 同裁切)
        function cellLumAt(px, py) {
            var vw = wpImg.clientWidth, vh = wpImg.clientHeight;
            var W = wpImg.naturalWidth, H = wpImg.naturalHeight;
            if (!W || !H || !vw || !vh) return 0.5;
            var sc = Math.max(vw / W, vh / H);
            var dw = W * sc, dh = H * sc;
            var sx = (px - (vw - dw) / 2) / sc;
            var sy = (py - (vh - dh) / 2) / sc;
            var ci = Math.max(0, Math.min(GRID_X - 1, Math.floor(sx / W * GRID_X)));
            var cj = Math.max(0, Math.min(GRID_Y - 1, Math.floor(sy / H * GRID_Y)));
            return brightGrid[cj * GRID_X + ci];
        }

        function hasOpaqueAncestor(el) {
            var node = el.parentNode;
            while (node && node !== document.body) {
                var bg = getComputedStyle(node).backgroundColor;
                if (bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)') return true;
                node = node.parentNode;
            }
            return false;
        }

        // 收集"直接落在壁纸上"的文本: 排除 Hero / 卡片内部; footer 透明后也纳入
        function collectAdaptEls() {
            adaptEls = [];
            if (!gridReady) return;
            var selector = 'main h1, main h2, main h3, main p, .site-footer span, .site-footer p, .site-footer a';
            document.querySelectorAll(selector).forEach(function (el) {
                if (el.closest('.hero')) return;
                var inFooter = !!el.closest('.site-footer');
                if (!inFooter && el.closest('a')) return; // 非 footer 链接保留主题强调色
                if (el.closest('.post-card, .dash-card, .project-item, .post-detail')) return; // 磨砂卡片自带对比, 文字保持主题色
                if (hasOpaqueAncestor(el)) return;
                if (el.querySelector('h1, h2, h3, p, span')) return; // 只处理叶子文本
                el.classList.add('adapt-live');
                adaptEls.push(el);
            });
        }

        function updateAdaptEls() {
            if (!gridReady) return;
            for (var k = 0; k < adaptEls.length; k++) {
                var el = adaptEls[k];
                var r = el.getBoundingClientRect();
                if (!r.width && !r.height) continue;
                var lum = cellLumAt(r.left + r.width / 2, r.top + r.height / 2);
                var dark = lum < 0.5;
                if (el.getAttribute('data-wptxt') !== (dark ? 'd' : 'l')) {
                    el.setAttribute('data-wptxt', dark ? 'd' : 'l');
                    el.style.color = dark ? '#ffffff' : '#0b0b0d';
                }
            }
        }

        function initAdaptive() {
            buildBrightnessGrid();
            collectAdaptEls();
            updateAdaptEls();
        }

        if (wpImg.complete && wpImg.naturalWidth > 0) {
            initAdaptive();
        } else {
            wpImg.addEventListener('load', initAdaptive);
        }
        var adaptTicking = false;
        function onAdaptiveScroll() {
            if (!adaptTicking) {
                requestAnimationFrame(function () { updateAdaptEls(); adaptTicking = false; });
                adaptTicking = true;
            }
        }
        window.addEventListener('scroll', onAdaptiveScroll, { passive: true });
        window.addEventListener('resize', onAdaptiveScroll, { passive: true });
    }

    /* ---------- 主题切换 ---------- */
    /* 遮罩透明度 = 基础值(后台配置) × 背景透明度滑块 × 主题修正(深色加深) */
    var bgFactor = 1;
    function applyOverlays() {
        var dark = (document.documentElement.getAttribute('data-theme') || 'light') === 'dark';
        document.querySelectorAll('.hero-bg-overlay, .site-wallpaper-overlay').forEach(function (o) {
            if (!o.dataset.base) o.dataset.base = o.dataset.overlay || o.style.opacity || '0.35';
            var v = parseFloat(o.dataset.base);
            if (dark) v = Math.min(v + 0.2, 0.7);
            o.style.opacity = (v * bgFactor).toFixed(3);
        });
    }
    function applyTheme(t) {
        document.documentElement.setAttribute('data-theme', t);
        try { localStorage.setItem('theme', t); } catch (e) {}
        applyOverlays();
    }
    applyOverlays();
    var themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function (e) {
            var cur = document.documentElement.getAttribute('data-theme') || 'light';
            var next = cur === 'light' ? 'dark' : 'light';
            // 圆形扩散过渡(View Transitions API)
            if (document.startViewTransition && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                var x = e.clientX, y = e.clientY;
                var endR = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
                var vt = document.startViewTransition(function () { applyTheme(next); });
                vt.ready.then(function () {
                    document.documentElement.animate(
                        { clipPath: ['circle(0px at ' + x + 'px ' + y + 'px)', 'circle(' + endR + 'px at ' + x + 'px ' + y + 'px)'] },
                        { duration: 500, easing: 'cubic-bezier(.22,.61,.36,1)', pseudoElement: '::view-transition-new(root)' }
                    );
                });
            } else {
                applyTheme(next);
            }
        });
    }

    /* ---------- 背景透明度滑块(顶栏右侧, 记忆到 localStorage) ---------- */
    (function () {
        var ctrl = document.getElementById('bgOpacityCtrl');
        var toggle = document.getElementById('bgOpacityToggle');
        var range = document.getElementById('bgOpacityRange');
        var value = document.getElementById('bgOpacityValue');
        if (!ctrl || !range) return;
        try {
            var saved = parseFloat(localStorage.getItem('bgOpacity'));
            if (!isNaN(saved) && saved >= 0 && saved <= 100) bgFactor = saved / 100;
        } catch (e) {}
        function applyBg(v) {
            bgFactor = v / 100;
            document.documentElement.style.setProperty('--bg-opacity', bgFactor.toFixed(2));
            try { localStorage.setItem('bgOpacity', String(Math.round(v))); } catch (e) {}
            if (value) value.textContent = Math.round(v) + '%';
            applyOverlays();
        }
        range.value = Math.round(bgFactor * 100);
        applyBg(parseFloat(range.value));
        range.addEventListener('input', function () { applyBg(parseFloat(this.value)); });
        if (toggle) {
            toggle.addEventListener('click', function () {
                var open = ctrl.classList.toggle('open');
                toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            });
        }
    })();

    /* ---------- 文章阅读风格切换(默认 / GitHub README, 记忆偏好) ---------- */
    (function () {
        var content = document.querySelector('.post-content');
        var switchBox = document.getElementById('postStyleSwitch');
        var btns = document.querySelectorAll('.post-style-btn');
        if (!content || !btns.length) return;
        // 无本地偏好时,以后台 SiteConfig 配置的默认风格为准
        var defaultStyle = switchBox && switchBox.getAttribute('data-default-style') === 'github'
            ? 'github' : 'default';
        var saved = defaultStyle;
        try {
            var t = localStorage.getItem('postStyle');
            if (t === 'github' || t === 'default') saved = t;
        } catch (e) {}
        function applyStyle(s) {
            content.classList.toggle('github-readme', s === 'github');
            btns.forEach(function (b) {
                var on = b.getAttribute('data-style') === s;
                b.classList.toggle('active', on);
                b.setAttribute('aria-pressed', on ? 'true' : 'false');
            });
            try { localStorage.setItem('postStyle', s); } catch (e) {}
        }
        btns.forEach(function (b) {
            b.addEventListener('click', function () { applyStyle(b.getAttribute('data-style')); });
        });
        applyStyle(saved);
    })();

    /* ---------- 阅读进度 + 导航滚动 + 返回顶部 ---------- */
    var progress = document.getElementById('readingProgress');
    var header = document.getElementById('siteHeader');
    var backTop = document.getElementById('backToTop');
    function updateScroll() {
        var h = document.documentElement;
        var scrollable = h.scrollHeight - h.clientHeight;
        if (progress) {
            var pct = scrollable <= 0 ? 0 : (h.scrollTop || document.body.scrollTop) / scrollable * 100;
            progress.style.width = Math.min(100, Math.max(0, pct)) + '%';
        }
        var y = window.pageYOffset || h.scrollTop || 0;
        if (header) header.classList.toggle('scrolled', y > 40);
        if (backTop) backTop.classList.toggle('show', y > 600);
    }
    updateScroll();
    var ticking = false;
    window.addEventListener('scroll', function () {
        if (!ticking) {
            requestAnimationFrame(function () { updateScroll(); ticking = false; });
            ticking = true;
        }
    }, { passive: true });
    window.addEventListener('resize', updateScroll, { passive: true });
    if (backTop) {
        backTop.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    /* ---------- Hero 标题动画(根据 data-animation 切换) ---------- */
    var heroTitle = document.querySelector('.hero-title');
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 通用:遍历标题节点,把文本拆成 <span class="char">,保留 .accent 等包裹
    function splitTitleChars(rootEl) {
        var tmp = document.createElement('div'); tmp.innerHTML = rootEl.innerHTML;
        var out = '';
        function wrapText(node, delay) {
            if (node.nodeType === 3) {
                var text = node.textContent;
                for (var i = 0; i < text.length; i++) {
                    out += '<span class="char" style="animation-delay:' + (delay + i * 0.04) + 's">' +
                           (text[i] === ' ' ? '&nbsp;' : text[i]) + '</span>';
                }
                return delay + text.length * 0.04;
            } else if (node.nodeType === 1) {
                var open = '<' + node.tagName.toLowerCase();
                for (var a = 0; a < node.attributes.length; a++) {
                    open += ' ' + node.attributes[a].name + '="' + node.attributes[a].value + '"';
                }
                open += '>';
                out += open;
                var d = delay;
                for (var c = 0; c < node.childNodes.length; c++) {
                    d = wrapText(node.childNodes[c], d);
                }
                out += '</' + node.tagName.toLowerCase() + '>';
                return d;
            }
            return delay;
        }
        var baseDelay = 0.1;
        while (tmp.firstChild) {
            baseDelay = wrapText(tmp.firstChild, baseDelay);
            tmp.removeChild(tmp.firstChild);
        }
        return out;
    }

    if (heroTitle && !reduceMotion) {
        var anim = heroTitle.getAttribute('data-animation') || 'char_rise';

        if (anim === 'char_rise') {
            // 逐字上升(默认):拆字 + charRise 动画
            heroTitle.innerHTML = splitTitleChars(heroTitle);
        } else if (anim === 'fade_up') {
            // 整块淡入上移:不拆字,给标题加 .anim-fade-up
            heroTitle.classList.add('anim-fade-up');
        } else if (anim === 'typewriter') {
            // 打字机:拆字后用 typewriter 动画逐字显现
            var typewriterHtml = splitTitleChars(heroTitle);
            heroTitle.innerHTML = typewriterHtml;
            heroTitle.classList.add('anim-typewriter');
            // 计算总时长,加光标闪烁
            var chars = heroTitle.querySelectorAll('.char');
            var lastDelay = chars.length ? parseFloat(chars[chars.length - 1].style.animationDelay || 0) : 0;
            heroTitle.style.setProperty('--tw-duration', (lastDelay + 0.6) + 's');
        } else if (anim === 'glitch') {
            // 故障抖动:拆字 + glitch 动画(随机延迟)
            var glitchHtml = splitTitleChars(heroTitle);
            heroTitle.innerHTML = glitchHtml;
            heroTitle.classList.add('anim-glitch');
            heroTitle.querySelectorAll('.char').forEach(function (ch, i) {
                ch.style.animationDelay = (Math.random() * 0.4 + i * 0.02) + 's';
            });
        } else if (anim === 'slide_reveal') {
            // 滑入遮罩揭示:拆字 + slideReveal 动画
            var slideHtml = splitTitleChars(heroTitle);
            heroTitle.innerHTML = slideHtml;
            heroTitle.classList.add('anim-slide-reveal');
        }
    }

    /* ---------- Hero 视差 ---------- */
    var hero = document.querySelector('.hero');
    var heroInner = document.querySelector('.hero-inner');
    if (hero && heroInner && !reduceMotion) {
        window.addEventListener('scroll', function () {
            var y = window.pageYOffset;
            if (y < window.innerHeight) {
                heroInner.style.transform = 'translateY(' + y * 0.25 + 'px)';
                heroInner.style.opacity = Math.max(0, 1 - y / (window.innerHeight * 0.7));
            }
        }, { passive: true });
    }

    /* ---------- Hero 动态壁纸视频:离开视口暂停 ---------- */
    var heroVideo = document.querySelector('.hero-bg-video');
    if (heroVideo && 'IntersectionObserver' in window) {
        var videoObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (en) {
                if (en.isIntersecting) {
                    var p = en.target.play();
                    if (p && typeof p.catch === 'function') p.catch(function () {});
                } else {
                    en.target.pause();
                }
            });
        }, { threshold: 0.05 });
        videoObserver.observe(heroVideo);
    }

    /* ---------- 卡片 3D 倾斜(仅桌面端, 减弱动效时跳过) ---------- */
    var isDesktop = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    if (isDesktop && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        document.querySelectorAll('.post-card').forEach(function (card) {
            card.addEventListener('mousemove', function (e) {
                var r = card.getBoundingClientRect();
                var px = (e.clientX - r.left) / r.width - 0.5;
                var py = (e.clientY - r.top) / r.height - 0.5;
                card.style.transform = 'perspective(900px) rotateY(' + (px * 5) + 'deg) rotateX(' + (-py * 5) + 'deg) translateY(-3px)';
            });
            card.addEventListener('mouseleave', function () {
                card.style.transform = '';
            });
        });
    }

    /* ---------- 磁吸按钮 ---------- */
    if (isDesktop && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        document.querySelectorAll('.btn-hero, .theme-toggle, .btn-submit').forEach(function (btn) {
            btn.addEventListener('mousemove', function (e) {
                var r = btn.getBoundingClientRect();
                var x = e.clientX - r.left - r.width / 2;
                var y = e.clientY - r.top - r.height / 2;
                btn.style.transform = 'translate(' + (x * 0.25) + 'px,' + (y * 0.35) + 'px)';
            });
            btn.addEventListener('mouseleave', function () { btn.style.transform = ''; });
        });
    }

    /* ---------- 数字计数动画 ---------- */
    function animateCount(el) {
        var target = parseInt(el.getAttribute('data-count'), 10);
        if (isNaN(target)) return;
        var dur = 1200, start = 0, t0 = null;
        function step(ts) {
            if (!t0) t0 = ts;
            var p = Math.min(1, (ts - t0) / dur);
            var eased = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.floor(start + (target - start) * eased);
            if (p < 1) requestAnimationFrame(step);
            else el.textContent = target;
        }
        requestAnimationFrame(step);
    }
    var countObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
            if (en.isIntersecting) {
                animateCount(en.target);
                countObserver.unobserve(en.target);
            }
        });
    }, { threshold: 0.6 });
    document.querySelectorAll('[data-count]').forEach(function (el) { countObserver.observe(el); });

    /* ---------- 滚动揭示 ---------- */
    var revealDirs = ['from-up', 'from-down', 'from-left', 'from-right'];
    var revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
            if (en.isIntersecting) {
                en.target.classList.add('is-visible');
                revealObserver.unobserve(en.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    document.querySelectorAll('.post-item, .archive-item, .cat-tag-item, .tag-cloud-item, .archive-year, .comments').forEach(function (el, i) {
        el.classList.add('reveal', revealDirs[i % revealDirs.length]);
        el.style.transitionDelay = (i % 4) * 80 + 'ms';
        revealObserver.observe(el);
    });

    /* ---------- 移动端导航 ---------- */
    var navToggle = document.getElementById('navToggle');
    var siteNav = document.getElementById('siteNav');
    if (navToggle && siteNav) {
        navToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            var open = siteNav.classList.toggle('open');
            navToggle.classList.toggle('active', open);
            navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
        document.addEventListener('click', function (e) {
            if (!siteNav.contains(e.target) && !navToggle.contains(e.target)) {
                siteNav.classList.remove('open');
                navToggle.classList.remove('active');
                navToggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    /* ---------- 外链新窗口 ---------- */
    document.querySelectorAll('a[href^="http"]').forEach(function (a) {
        var href = a.getAttribute('href') || '';
        if (href.indexOf(location.origin) !== 0 && href.indexOf('mailto:') !== 0) {
            a.setAttribute('target', '_blank');
            a.setAttribute('rel', 'noopener noreferrer');
        }
    });

    /* ---------- 图片懒加载 ---------- */
    if ('loading' in HTMLImageElement.prototype) {
        document.querySelectorAll('.post-content img:not([loading])').forEach(function (img) {
            img.setAttribute('loading', 'lazy');
        });
    }

    /* ---------- 评论 AJAX(可选) ---------- */
    var commentForm = document.querySelector('.comment-form');
    if (commentForm && commentForm.dataset.ajax === 'on') {
        commentForm.addEventListener('submit', function (e) {
            e.preventDefault();
            var form = e.target;
            var submitBtn = form.querySelector('.btn-submit');
            var formData = new FormData(form);
            var action = form.getAttribute('action') || window.location.pathname;
            var apiUrl = action.replace(/#.*$/, '') + (action.indexOf('comment/') === -1 ? 'comment/' : '');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.dataset.originalText = submitBtn.textContent;
                submitBtn.textContent = '提交中…';
            }
            fetch(apiUrl, { method: 'POST', body: formData, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.ok) {
                        alert(data.comment.approved ? '评论成功,已发布。' : '评论已提交,审核后显示。');
                        form.reset();
                    } else {
                        alert('提交失败:' + JSON.stringify(data.errors));
                    }
                })
                .catch(function () { alert('网络错误,请重试。'); })
                .finally(function () {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = submitBtn.dataset.originalText || '提交评论';
                    }
                });
        });
    }

    /* ============================================================
       首页功能卡片: 实时时钟 + 问候语
       ============================================================ */
    function startClock() {
        var $time = document.getElementById('clockTime');
        if (!$time) return;
        var $date = document.getElementById('clockDate');
        var $weekday = document.getElementById('clockWeekday');
        var $greet = document.getElementById('clockGreeting');
        var weekdays = ['星期日','星期一','星期二','星期三','星期四','星期五','星期六'];
        function pad(n){ return n < 10 ? '0' + n : n; }
        function greet(h){
            if (h < 6)  return '凌晨好 · 注意休息';
            if (h < 11) return '早上好';
            if (h < 13) return '中午好';
            if (h < 18) return '下午好';
            if (h < 22) return '晚上好';
            return '夜深了 · 早些睡';
        }
        function tick(){
            var d = new Date();
            $time.textContent = pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
            if ($date)    $date.textContent = d.getFullYear() + '/' + pad(d.getMonth() + 1) + '/' + pad(d.getDate());
            if ($weekday) $weekday.textContent = weekdays[d.getDay()];
            if ($greet)   $greet.textContent = greet(d.getHours());
        }
        tick();
        setInterval(tick, 1000);
    }
    startClock();

    /* ============================================================
       首页功能卡片: 天气 (后端代理: 和风天气,无 Key 回退 Open-Meteo)
       ============================================================ */
    // 和风天气 icon 编码 -> emoji
    var QICON = {
        100: '☀️', 101: '⛅', 102: '🌤️', 103: '🌤️', 104: '☁️',
        150: '🌙', 151: '☁️', 152: '☁️', 153: '☁️',
        300: '🌦️', 301: '⛈️', 302: '⛈️', 303: '⛈️', 304: '⛈️',
        305: '🌧️', 306: '🌧️', 307: '🌧️', 308: '⛈️', 309: '🌦️', 310: '🌧️',
        311: '⛈️', 312: '⛈️', 313: '🌧️', 314: '🌧️', 315: '🌧️', 316: '⛈️',
        317: '⛈️', 318: '⛈️', 350: '🌦️', 351: '⛈️', 399: '🌧️',
        400: '🌨️', 401: '🌨️', 402: '❄️', 403: '❄️', 404: '🌨️', 405: '🌨️',
        406: '🌨️', 407: '🌨️', 408: '🌨️', 409: '❄️', 410: '❄️',
        456: '🌨️', 457: '🌨️', 499: '❄️',
        500: '🌫️', 501: '🌫️', 502: '🌫️', 503: '🌫️', 504: '🌫️',
        507: '🌪️', 508: '🌪️', 509: '🌫️', 510: '🌫️', 511: '🌫️',
        512: '🌫️', 513: '🌫️', 514: '🌫️', 515: '🌫️',
        900: '☀️', 901: '❄️', 999: '🌈'
    };
    function loadWeather() {
        var elTemp = document.getElementById('weatherTemp');
        if (!elTemp) return;
        var elDesc = document.getElementById('weatherDesc');
        var elLoc  = document.getElementById('weatherLoc');
        var elIcon = document.getElementById('weatherIcon');

        // WMO 天气代码 -> [中文描述, emoji](Open-Meteo 兜底时用)
        var WMO = {
             0:['晴','☀️'],   1:['大部晴朗','🌤️'], 2:['局部多云','⛅'], 3:['阴','☁️'],
            45:['雾','🌫️'], 48:['雾凇','🌫️'],
            51:['小毛毛雨','🌦️'], 53:['毛毛雨','🌦️'], 55:['大毛毛雨','🌧️'],
            61:['小雨','🌧️'],   63:['中雨','🌧️'],   65:['大雨','⛈️'],
            71:['小雪','🌨️'],   73:['中雪','🌨️'],   75:['大雪','❄️'], 77:['雪粒','🌨️'],
            80:['阵雨','🌦️'],   81:['强阵雨','⛈️'], 82:['暴雨','⛈️'],
            85:['阵雪','🌨️'],   86:['强阵雪','🌨️'],
            95:['雷暴','⛈️'],   96:['雷暴·小冰雹','⛈️'], 99:['雷暴·大冰雹','⛈️']
        };
        function show(city, temp, icon, text, source){
            var emoji, desc;
            if (source === 'qweather') {
                emoji = QICON[icon] || '🌈';
                desc = text || '';
            } else {
                var w = WMO[icon] || ['—','🌈'];
                emoji = w[1]; desc = w[0];
            }
            elTemp.textContent = Math.round(temp);
            if (elDesc) elDesc.textContent = desc;
            if (elLoc)  elLoc.textContent = '📍 ' + city;
            if (elIcon) elIcon.innerHTML = '<span style="font-size:3rem;line-height:1;display:inline-block;">' + emoji + '</span>';
        }
        function fail(msg){
            if (elDesc) elDesc.textContent = msg || '暂不可用';
            if (elLoc)  elLoc.textContent = '📍 离线模式';
            elTemp.textContent = '—';
        }
        // 定位失败时的默认城市回退(柳州),避免卡片显示错误文案
        var DEFAULT_LOC = ['24.3264', '109.4286'];
        function fetchWeather(lat, lon) {
            fetch('/api/weather/?lat=' + lat + '&lon=' + lon, { method: 'GET' })
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    if (!d.ok) throw new Error(d.error || '接口错误');
                    show(d.city, d.temp, d.icon, d.text, d.source);
                })
                .catch(function () { fail('天气数据加载失败'); });
        }
        if (!navigator.geolocation) { return fetchWeather(DEFAULT_LOC[0], DEFAULT_LOC[1]); }
        try {
            navigator.geolocation.getCurrentPosition(
                function (pos) {
                    fetchWeather(pos.coords.latitude.toFixed(4), pos.coords.longitude.toFixed(4));
                },
                function () { fetchWeather(DEFAULT_LOC[0], DEFAULT_LOC[1]); },
                { timeout: 6000, enableHighAccuracy: false }
            );
        } catch (e) { fetchWeather(DEFAULT_LOC[0], DEFAULT_LOC[1]); }
    }
    loadWeather();

    /* ---------- 圆环跟随光标: 弹性缓动 + 可交互放大(参照最初版本) ---------- */
    (function () {
        if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
        var ring = document.getElementById('cursorRing');
        if (!ring) return;
        var INTERACT = 'a, button, select, summary, label, [role="button"], .btn, input[type="checkbox"], input[type="radio"]';
        var mx = -100, my = -100, rx = -100, ry = -100, shown = false;
        document.addEventListener('mousemove', function (e) {
            mx = e.clientX; my = e.clientY;
            if (!shown) {
                shown = true;
                rx = mx; ry = my;
                ring.classList.add('visible');
            }
        }, { passive: true });
        // 圆环弹性缓动跟随(持续循环)
        (function loop() {
            rx += (mx - rx) * 0.16;
            ry += (my - ry) * 0.16;
            ring.style.transform = 'translate3d(' + rx + 'px,' + ry + 'px,0)';
            requestAnimationFrame(loop);
        })();
        // 悬停可交互元素: 圆环放大提示
        document.addEventListener('mouseover', function (e) {
            var t = e.target;
            if (t && t.closest && t.closest(INTERACT)) ring.classList.add('hovering');
        });
        document.addEventListener('mouseout', function (e) {
            var t = e.target;
            if (t && t.closest && t.closest(INTERACT)) ring.classList.remove('hovering');
        });
        document.addEventListener('mouseleave', function () {
            ring.classList.remove('visible');
        });
        document.addEventListener('mouseenter', function () {
            if (shown) ring.classList.add('visible');
        });
    })();

})();
