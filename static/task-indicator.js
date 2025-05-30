/**
 * 全局任务状态指示器组件
 * 可以在任何页面的导航栏中使用
 */
class TaskIndicator {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentTask = null;
        this.intervalId = null;
        this.init();
    }

    init() {
        if (!this.container) return;
        
        // 创建任务指示器HTML
        this.container.innerHTML = `
            <div id="task-indicator" class="task-indicator hidden">
                <div class="task-content">
                    <div class="task-icon">🚀</div>
                    <div class="task-info">
                        <div class="task-title"></div>
                        <div class="task-progress-bar">
                            <div class="task-progress-fill"></div>
                        </div>
                        <div class="task-percentage">0%</div>
                    </div>
                    <a href="/tasks" class="task-link" title="查看详情">📋</a>
                </div>
            </div>
        `;

        // 添加CSS样式
        this.addStyles();
        
        // 开始监控任务状态
        this.startMonitoring();
    }

    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .task-indicator {
                position: fixed;
                top: 80px;
                right: 20px;
                background: linear-gradient(135deg, #FFB7D1, #C8A8E9);
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(255, 183, 209, 0.3);
                padding: 12px 16px;
                z-index: 1000;
                max-width: 300px;
                transition: all 0.3s ease;
                border: 2px solid rgba(255, 255, 255, 0.2);
            }

            .task-indicator.hidden {
                opacity: 0;
                transform: translateX(100%);
                pointer-events: none;
            }

            .task-indicator:not(.hidden) {
                opacity: 1;
                transform: translateX(0);
            }

            .task-content {
                display: flex;
                align-items: center;
                gap: 12px;
                color: white;
            }

            .task-icon {
                font-size: 20px;
                animation: spin 2s linear infinite;
            }

            .task-info {
                flex: 1;
                min-width: 0;
            }

            .task-title {
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 4px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .task-progress-bar {
                width: 100%;
                height: 4px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 2px;
                overflow: hidden;
                margin-bottom: 2px;
            }

            .task-progress-fill {
                height: 100%;
                background: rgba(255, 255, 255, 0.8);
                border-radius: 2px;
                transition: width 0.3s ease;
                width: 0%;
            }

            .task-percentage {
                font-size: 12px;
                font-weight: 500;
                opacity: 0.9;
            }

            .task-link {
                color: white;
                text-decoration: none;
                font-size: 18px;
                opacity: 0.8;
                transition: opacity 0.2s ease;
            }

            .task-link:hover {
                opacity: 1;
            }

            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }

            /* 暗色模式支持 */
            @media (prefers-color-scheme: dark) {
                .task-indicator {
                    background: linear-gradient(135deg, #8B5CF6, #EC4899);
                }
            }
        `;
        document.head.appendChild(style);
    }

    async fetchCurrentTask() {
        try {
            const response = await fetch('/api/tasks/current');
            if (response.ok) {
                const data = await response.json();
                // 只有当任务存在且状态为运行中时才显示
                if (data && data.status === 'running') {
                    this.updateTaskIndicator(data);
                } else {
                    this.hideIndicator();
                }
            } else {
                this.hideIndicator();
            }
        } catch (error) {
            console.error('获取当前任务失败:', error);
            this.hideIndicator();
        }
    }

    updateTaskIndicator(task) {
        if (!task || !task.status || task.status !== 'running' || !this.container) {
            this.hideIndicator();
            return;
        }

        const indicator = this.container.querySelector('#task-indicator');
        const title = indicator.querySelector('.task-title');
        const progressFill = indicator.querySelector('.task-progress-fill');
        const percentage = indicator.querySelector('.task-percentage');

        // 更新任务标题
        title.textContent = task.title || '执行中...';

        // 更新进度
        const progress = task.progress ? Math.round(task.progress.percentage || 0) : 0;
        progressFill.style.width = `${progress}%`;
        percentage.textContent = `${progress}%`;

        // 显示指示器
        indicator.classList.remove('hidden');
        this.currentTask = task;
    }

    hideIndicator() {
        const indicator = this.container.querySelector('#task-indicator');
        if (indicator) {
            indicator.classList.add('hidden');
        }
        this.currentTask = null;
    }

    startMonitoring() {
        // 立即检查一次
        this.fetchCurrentTask();
        
        // 每2秒检查一次任务状态
        this.intervalId = setInterval(() => {
            this.fetchCurrentTask();
        }, 2000);
    }

    stopMonitoring() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    destroy() {
        this.stopMonitoring();
        this.hideIndicator();
    }
}

// 导出为全局使用
window.TaskIndicator = TaskIndicator;

// 自动初始化（如果存在容器）
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('task-indicator-container')) {
        window.globalTaskIndicator = new TaskIndicator('task-indicator-container');
    }
}); 