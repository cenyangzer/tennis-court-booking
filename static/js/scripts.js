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

    // 实现轮播图自动轮播（bootstrap 未加载时跳过，避免脚本中断）
    const carousel = document.querySelector('#carouselExampleIndicators');
    if (carousel && typeof bootstrap !== 'undefined' && bootstrap.Carousel) {
        new bootstrap.Carousel(carousel, {
            interval: 5000,
            wrap: true
        });
    }

    // 窗口滚动事件：导航栏滚动时添加阴影
    window.addEventListener('scroll', function() {
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            if (window.scrollY > 50) {
                navbar.classList.add('shadow');
            } else {
                navbar.classList.remove('shadow');
            }
        }
    });
});
