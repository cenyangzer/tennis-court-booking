// 等待DOM加载完成
 document.addEventListener('DOMContentLoaded', function() {
    // 平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            document.querySelector(targetId).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // 表单验证
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            const requiredFields = this.querySelectorAll('[required]');
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('is-invalid');
                } else {
                    field.classList.remove('is-invalid');
                }
            });

            // 密码确认验证
            const passwordField = this.querySelector('input[name="password"]');
            const confirmPasswordField = this.querySelector('input[name="confirm_password"]');
            
            if (passwordField && confirmPasswordField) {
                if (passwordField.value !== confirmPasswordField.value) {
                    isValid = false;
                    confirmPasswordField.classList.add('is-invalid');
                    const errorElement = document.createElement('div');
                    errorElement.className = 'invalid-feedback';
                    errorElement.textContent = '密码不匹配';
                    if (!confirmPasswordField.nextElementSibling || !confirmPasswordField.nextElementSibling.classList.contains('invalid-feedback')) {
                        confirmPasswordField.parentNode.appendChild(errorElement);
                    }
                } else {
                    confirmPasswordField.classList.remove('is-invalid');
                    const errorElement = confirmPasswordField.parentNode.querySelector('.invalid-feedback');
                    if (errorElement) {
                        errorElement.remove();
                    }
                }
            }

            if (!isValid) {
                e.preventDefault();
                // 滚动到第一个错误字段
                const firstError = this.querySelector('.is-invalid');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstError.focus();
                }
            }
        });

        // 输入框实时验证
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                if (this.hasAttribute('required')) {
                    if (this.value.trim()) {
                        this.classList.remove('is-invalid');
                    }
                }
            });
        });
    });

    // 时间选择器限制
    const startTimeInput = document.getElementById('start_time');
    const endTimeInput = document.getElementById('end_time');
    
    if (startTimeInput && endTimeInput) {
        // 设置最小时间为当前时间
        const now = new Date();
        const minDateTime = now.toISOString().slice(0, 16);
        startTimeInput.min = minDateTime;
        
        startTimeInput.addEventListener('change', function() {
            // 设置结束时间的最小值为开始时间
            endTimeInput.min = this.value;
            
            // 如果结束时间早于开始时间，清空结束时间
            if (endTimeInput.value && endTimeInput.value <= this.value) {
                endTimeInput.value = '';
            }
        });

        // 计算时长和费用
        const calculateDurationAndCost = function() {
            if (startTimeInput.value && endTimeInput.value) {
                const startTime = new Date(startTimeInput.value);
                const endTime = new Date(endTimeInput.value);
                
                if (endTime > startTime) {
                    const durationMs = endTime - startTime;
                    const durationHours = Math.ceil(durationMs / (1000 * 60 * 60));
                    
                    // 获取价格（假设从HTML中提取或通过DOM元素获取）
                    const pricePerHourElement = document.getElementById('price_per_hour');
                    let pricePerHour = 100; // 默认价格
                    
                    if (pricePerHourElement) {
                        pricePerHour = parseFloat(pricePerHourElement.textContent.replace(/[^\d.]/g, ''));
                    }
                    
                    const totalCost = durationHours * pricePerHour;
                    
                    // 更新时长和费用显示
                    const durationElement = document.getElementById('duration_display');
                    const costElement = document.getElementById('cost_display');
                    
                    if (durationElement) durationElement.textContent = `${durationHours} 小时`;
                    if (costElement) costElement.textContent = `¥${totalCost.toFixed(2)}`;
                }
            }
        };
        
        startTimeInput.addEventListener('change', calculateDurationAndCost);
        endTimeInput.addEventListener('change', calculateDurationAndCost);
    }

    // 消息提示自动隐藏
    const alertElements = document.querySelectorAll('.alert');
    alertElements.forEach(alert => {
        setTimeout(() => {
            alert.classList.add('fade-out');
            setTimeout(() => {
                alert.remove();
            }, 500);
        }, 5000);
    });

    // 移动端菜单切换
    const mobileMenuToggle = document.querySelector('.navbar-toggler');
    const mobileMenu = document.querySelector('.navbar-collapse');
    
    if (mobileMenuToggle && mobileMenu) {
        mobileMenuToggle.addEventListener('click', function() {
            mobileMenu.classList.toggle('show');
        });
    }

    // 加载更多内容
    const loadMoreButton = document.querySelector('.load-more-btn');
    if (loadMoreButton) {
        loadMoreButton.addEventListener('click', function() {
            const currentPage = parseInt(this.dataset.page || 1);
            const nextPage = currentPage + 1;
            const url = new URL(window.location.href);
            url.searchParams.set('page', nextPage);
            
            fetch(url)
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newItems = doc.querySelectorAll('.card-grid .card');
                    
                    if (newItems.length > 0) {
                        const cardGrid = document.querySelector('.card-grid');
                        newItems.forEach(item => cardGrid.appendChild(item));
                        this.dataset.page = nextPage;
                    } else {
                        this.disabled = true;
                        this.textContent = '没有更多内容了';
                    }
                })
                .catch(error => console.error('加载更多内容失败:', error));
        });
    }

    // 图片预览
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const previewElement = this.closest('.form-group').querySelector('.image-preview');
            if (previewElement && this.files && this.files[0]) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    previewElement.src = e.target.result;
                    previewElement.style.display = 'block';
                }
                
                reader.readAsDataURL(this.files[0]);
            }
        });
    });

    // 实现轮播图自动轮播（如果没有使用Bootstrap的自动轮播）
    const carousel = document.querySelector('#carouselExampleIndicators');
    if (carousel) {
        const carouselInstance = new bootstrap.Carousel(carousel, {
            interval: 5000,
            wrap: true
        });
    }

    // 页面加载完成后的动画效果
    const animateOnLoad = function() {
        const fadeElements = document.querySelectorAll('.fade-in');
        fadeElements.forEach((element, index) => {
            setTimeout(() => {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, index * 100);
        });
    };

    // 执行页面加载动画
    animateOnLoad();

    // 窗口滚动事件
    window.addEventListener('scroll', function() {
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            if (window.scrollY > 50) {
                navbar.classList.add('bg-dark');
                navbar.classList.add('shadow-md');
            } else {
                navbar.classList.remove('bg-dark');
                navbar.classList.remove('shadow-md');
            }
        }

        // 滚动到顶部按钮
        const scrollTopBtn = document.querySelector('.scroll-top-btn');
        if (scrollTopBtn) {
            if (window.scrollY > 300) {
                scrollTopBtn.style.display = 'block';
            } else {
                scrollTopBtn.style.display = 'none';
            }
        }
    });

    // 滚动到顶部功能
    const scrollTopBtn = document.querySelector('.scroll-top-btn');
    if (scrollTopBtn) {
        scrollTopBtn.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
});