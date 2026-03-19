/**
 * 番剧智能助手 - 前端交互脚本
 * 基于设计文档: 前端对话框设计说明文档.md
 */

class AnimeChatbot {
    constructor() {
        this.messagesContainer = document.getElementById('messages');
        this.userInput = document.getElementById('userInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.apiStatus = document.getElementById('apiStatus');
        this.apiBase = 'http://localhost:8000';
        
        // 加载状态
        this.isLoading = false;
        this.abortController = null;
        
        // 待发送消息队列（AI 回复时用户发送的消息会进入队列）
        this.pendingMessages = [];
        
        // 对话历史
        this.messages = [];
        
        this.init();
    }
    
    init() {
        // 绑定发送按钮事件
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        
        // 绑定输入框回车事件
        this.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
        
        // 绑定快捷操作按钮
        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const query = btn.dataset.query;
                this.userInput.value = query;
                this.sendMessage();
            });
        });
        
        // 检查 API 状态
        this.checkApiStatus();
        
        // 聚焦输入框
        this.userInput.focus();
    }
    
    async checkApiStatus() {
        try {
            const response = await fetch(`${this.apiBase}/health`, { method: 'GET' });
            if (response.ok) {
                this.apiStatus.textContent = 'API 状态: ✓ 在线';
                this.apiStatus.classList.add('online');
            } else {
                this.apiStatus.textContent = 'API 状态: ✗ 离线';
            }
        } catch (e) {
            this.apiStatus.textContent = 'API 状态: ✗ 离线';
        }
    }
    
    async sendMessage() {
        const message = this.userInput.value.trim();
        if (!message) return;
        
        // 如果 AI 正在回复，将消息加入待发送队列
        if (this.isLoading) {
            this.pendingMessages.push(message);
            this.userInput.value = '';  // 清空输入框
            this.updatePendingIndicator();  // 显示待发送提示
            return;
        }
        
        // 清空输入框
        this.userInput.value = '';
        
        // 添加用户消息
        this.addMessage('user', message);
        
        // 创建AI消息容器
        const botMsg = this.addAssistantMessage();
        
        // 获取思考过程和内容区域
        const thinkingContainer = botMsg.querySelector('.thinking-container');
        const contentArea = botMsg.querySelector('.content-area');
        
        // 设置加载状态（会禁用输入和按钮）
        this.setLoading(true);
        
        // 发送请求
        await this.makeRequest(message, thinkingContainer, contentArea);
    }
    
    // 发送请求的逻辑（抽离出来以便复用）
    async makeRequest(message, thinkingContainer, contentArea) {
        try {
            this.abortController = new AbortController();
            const response = await fetch(`${this.apiBase}/api/chat/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    query: message,
                    history: this.getHistory()
                }),
                signal: this.abortController.signal
            });
            
            if (!response.ok) {
                throw new Error(`API 请求失败: ${response.status}`);
            }
            
            // 处理流式响应
            await this.processStream(response, thinkingContainer, contentArea);
            
        } catch (e) {
            if (e.name === 'AbortError') {
                // 用户主动停止
                contentArea.innerHTML += '<br>[已停止]';
            } else if (e.name === 'TypeError' && e.message.includes('fetch')) {
                // 网络错误
                contentArea.innerHTML += '<br><span style="color: orange;">⚠️ 连接已断开，请检查网络后重试</span>';
            } else {
                console.error('请求错误:', e);
                contentArea.innerHTML = `抱歉，服务暂时不可用。<br>错误信息: ${e.message}`;
            }
        }
        
        // 结束加载状态
        this.setLoading(false);
        this.abortController = null;
        
        // 处理待发送队列中的消息
        this.processPendingQueue();
    }
    
    // 处理待发送队列
    processPendingQueue() {
        if (this.pendingMessages.length > 0 && !this.isLoading) {
            const nextMessage = this.pendingMessages.shift();
            this.updatePendingIndicator();
            
            // 延迟一点发送，让 UI 有时间更新
            setTimeout(() => {
                this.sendMessageWithContent(nextMessage);
            }, 100);
        }
    }
    
    // 直接使用指定内容发送消息（不经过输入框）
    sendMessageWithContent(message) {
        if (!message) return;
        
        // 添加用户消息
        this.addMessage('user', message);
        
        // 创建AI消息容器
        const botMsg = this.addAssistantMessage();
        
        // 获取思考过程和内容区域
        const thinkingContainer = botMsg.querySelector('.thinking-container');
        const contentArea = botMsg.querySelector('.content-area');
        
        // 设置加载状态
        this.setLoading(true);
        
        // 发送请求
        this.makeRequest(message, thinkingContainer, contentArea);
    }
    
    // 更新待发送提示
    updatePendingIndicator() {
        // 移除旧的提示
        const oldIndicator = document.querySelector('.pending-indicator');
        if (oldIndicator) oldIndicator.remove();
        
        if (this.pendingMessages.length > 0) {
            const indicator = document.createElement('div');
            indicator.className = 'pending-indicator';
            indicator.style.cssText = 'position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); background: #ff9800; color: white; padding: 8px 16px; border-radius: 20px; font-size: 14px; z-index: 1000;';
            indicator.textContent = `📝 ${this.pendingMessages.length} 条消息等待中...`;
            document.body.appendChild(indicator);
        }
    }
    
    async processStream(response, thinkingContainer, contentArea) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let isAborted = false;
        
        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            this.handleStreamData(data, thinkingContainer, contentArea);
                        } catch (e) {
                            // 忽略解析错误
                        }
                    }
                }
            }
        } catch (e) {
            // 检查是否是用户主动中止
            if (e.name === 'AbortError') {
                isAborted = true;
            }
            // 其他错误（网络断开等）不显示额外的错误信息
            // 让 makeRequest 的 catch 块统一处理
            console.warn('流式响应中断:', e.name, e.message);
        }
        
        // 完成后添加到历史（只有正常完成或用户中止时才添加）
        if (!isAborted) {
            const content = contentArea.innerHTML;
            if (content) {
                this.messages.push({ role: 'assistant', content: content });
            }
        }
    }
    
    handleStreamData(data, thinkingContainer, contentArea) {
        const type = data.type;
        
        // 获取思考内容区域
        const thinkingContent = thinkingContainer.querySelector('.thinking-content');
        
        // 如果有增量数据，添加到思考过程区域
        if (data.intent_delta || data.params_delta || data.plan_delta || data.exec_delta) {
            this.handleThinkingIncremental(data, thinkingContent);
            return;
        }
        
        switch (type) {
            case 'thinking':
                // 思考过程
                this.handleThinking(data, thinkingContent);
                break;
            case 'content':
                // 内容（已废弃，使用output）
                break;
            case 'output':
                // 输出内容
                this.handleOutput(data, contentArea);
                break;
            case 'step_status':
                // 步骤状态
                this.handleStepStatus(data, thinkingContent);
                break;
            case 'plan':
                // 执行计划
                this.handlePlan(data, thinkingContent);
                break;
            case 'done':
                // 完成
                this.scrollToBottom();
                break;
            case 'error':
                // 错误
                contentArea.innerHTML += `<br><span style="color: red;">错误: ${data.content || data.message}</span>`;
                break;
            default:
                // 忽略未知类型
                break;
        }
    }
    
    // 处理增量数据（意图、计划、执行的增量更新）- 流式输出
    handleThinkingIncremental(data, container) {
        // 显示思考过程容器
        const thinkingContainer = container.closest('.thinking-container');
        if (thinkingContainer && thinkingContainer.style.display === 'none') {
            thinkingContainer.style.display = 'block';
        }
        
        // 意图解析 - parsing状态
        if (data.status === 'parsing') {
            if (data.intent_delta) {
                let step = container.querySelector('.step-intent');
                if (!step) {
                    step = document.createElement('div');
                    step.className = 'process-step step-intent';
                    step.innerHTML = `<div class="step-title">🎯 意图解析</div><div class="step-content parsing"></div>`;
                    container.appendChild(step);
                }
                step.querySelector('.step-content').textContent = data.intent_delta;
            }
            if (data.params_delta) {
                let step = container.querySelector('.step-params');
                if (!step) {
                    step = document.createElement('div');
                    step.className = 'process-step step-params';
                    step.innerHTML = `<div class="step-content"></div>`;
                    container.appendChild(step);
                }
                step.querySelector('.step-content').textContent = '参数: ' + data.params_delta;
            }
        }
        
        // 意图完成 - done状态
        if (data.status === 'done' && data.type === 'intent' && data.intent) {
            let step = container.querySelector('.step-intent');
            if (!step) {
                step = document.createElement('div');
                step.className = 'process-step step-intent';
                container.appendChild(step);
            }
            step.className = 'process-step step-intent done';
            step.innerHTML = `<div class="step-title">🎯 意图解析</div><div class="step-content done">✅ ${this.getIntentName(data.intent)} <br><small>${this.escapeHtml(JSON.stringify(data.params))}</small></div>`;
        }
        
        // 计划生成 - parsing状态
        if (data.type === 'plan' && data.status === 'planning' && data.plan_delta) {
            let step = container.querySelector('.step-plan');
            if (!step) {
                step = document.createElement('div');
                step.className = 'process-step step-plan';
                step.innerHTML = `<div class="step-title">📋 执行计划</div><div class="step-content"></div>`;
                container.appendChild(step);
            }
            const contentDiv = step.querySelector('.step-content');
            if (contentDiv.textContent) {
                contentDiv.innerHTML += '<br>' + data.plan_delta;
            } else {
                contentDiv.textContent = data.plan_delta;
            }
        }
        
        // 计划完成 - done状态
        if (data.type === 'plan' && data.status === 'done' && data.plan) {
            let step = container.querySelector('.step-plan');
            if (!step) {
                step = document.createElement('div');
                step.className = 'process-step step-plan';
                container.appendChild(step);
            }
            step.className = 'process-step step-plan done';
            let planHtml = '<div class="step-title">📋 执行计划</div><div class="step-content done">';
            data.plan.forEach((p, i) => {
                planHtml += `<div>${i+1}. ${p.tool}: ${JSON.stringify(p.params)}</div>`;
            });
            planHtml += '</div>';
            step.innerHTML = planHtml;
        }
        
        // 工具执行 - executing状态
        if (data.type === 'execution' && data.status === 'executing' && data.exec_delta) {
            let step = container.querySelector('.step-exec');
            if (!step) {
                step = document.createElement('div');
                step.className = 'process-step step-exec';
                step.innerHTML = `<div class="step-title">🔧 工具执行</div><div class="step-content"></div>`;
                container.appendChild(step);
            }
            const contentDiv = step.querySelector('.step-content');
            if (contentDiv.innerHTML) {
                contentDiv.innerHTML += '<br>' + data.exec_delta;
            } else {
                contentDiv.textContent = data.exec_delta;
            }
        }
        
        // 执行完成 - done状态
        if (data.type === 'execution' && data.status === 'done' && data.results) {
            let step = container.querySelector('.step-exec');
            if (!step) {
                step = document.createElement('div');
                step.className = 'process-step step-exec';
                container.appendChild(step);
            }
            step.className = 'process-step step-exec done';
            step.innerHTML = `<div class="step-title">🔧 工具执行</div><div class="step-content done">✅ 执行完成</div>`;
        }
        
        this.scrollToBottom();
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    getIntentName(intent) {
        const names = {
            'greeting': '打招呼',
            'capability': '询问能力',
            'query': '番剧查询',
            'detail': '番剧详情',
            'ranking': '排行榜',
            'thanks': '感谢',
            'chat': '闲聊'
        };
        return names[intent] || intent;
    }
    
    handleThinking(data, container) {
        // 思考过程 - 直接追加内容
        const content = data.delta || data.thought || '';
        if (content) {
            const p = document.createElement('p');
            p.textContent = content;
            container.appendChild(p);
            this.scrollToBottom();
        }
    }
    
    handleOutput(data, contentArea) {
        const status = data.status;
        
        if (status === 'streaming') {
            // 流式输出 - 增量追加
            const delta = data.content_delta || data.content || '';
            if (delta) {
                contentArea.innerHTML += delta;
                this.scrollToBottom();
            }
        } else if (status === 'done') {
            // 完成 - 将现有的纯文本内容转换为 Markdown 渲染
            // 不再替换 innerHTML，保留流式显示的过程
            const currentContent = contentArea.innerHTML;
            if (currentContent) {
                // 将现有内容作为纯文本，然后渲染 Markdown
                // 由于内容已经是 HTML 形式，我们需要将 HTML 实体转回文本再渲染
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = currentContent;
                const textContent = tempDiv.textContent || currentContent;
                
                // 使用 Markdown 渲染
                if (window.md) {
                    contentArea.innerHTML = window.md.render(textContent);
                } else if (window.marked) {
                    contentArea.innerHTML = window.marked.parse(textContent);
                }
                // 如果没有 Markdown 库，保留原样
            }
            this.scrollToBottom();
        }
    }
    
    handleStepStatus(data, container) {
        const step = data.step || 1;
        const status = data.status || 'running';
        const tool = data.tool || '';
        
        // 创建步骤状态元素
        const stepDiv = document.createElement('div');
        stepDiv.className = 'step-item';
        
        const icons = {
            'running': '🔄',
            'completed': '✅',
            'failed': '❌',
            'fallback_success': '⚠️',
            'error': '❌'
        };
        
        const colors = {
            'running': '#2196f3',
            'completed': '#4caf50',
            'failed': '#f44336',
            'fallback_success': '#ff9800',
            'error': '#e91e63'
        };
        
        stepDiv.innerHTML = `
            <span class="step-icon" style="color: ${colors[status] || '#999'}">${icons[status] || '⬜'}</span>
            <span class="step-text">步骤${step}: ${tool || '处理中'}</span>
        `;
        
        container.appendChild(stepDiv);
        this.scrollToBottom();
    }
    
    handlePlan(data, container) {
        const plan = data.plan || [];
        if (plan.length === 0) return;
        
        // 创建计划元素
        const planDiv = document.createElement('div');
        planDiv.className = 'plan-item';
        
        let planHtml = '<div class="plan-title">📋 执行计划</div>';
        plan.forEach((step, i) => {
            planHtml += `<div class="plan-step">⏳ ${i + 1}. ${step.tool}: ${JSON.stringify(step.params)}</div>`;
        });
        
        planDiv.innerHTML = planHtml;
        container.appendChild(planDiv);
        this.scrollToBottom();
    }
    
    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const avatar = role === 'user' ? '👤' : '🤖';
        
        messageDiv.innerHTML = `
            <div class="avatar">${avatar}</div>
            <div class="content">${content}</div>
        `;
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // 添加到历史
        this.messages.push({ role, content });
        
        return messageDiv;
    }
    
    addAssistantMessage() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';
        
        // 使用设计文档中的结构
        messageDiv.innerHTML = `
            <div class="avatar">🤖</div>
            <div class="content">
                <!-- 思考过程容器（默认收起） -->
                <div class="thinking-container" style="display: none;">
                    <div class="thinking-header" onclick="toggleThinking(this)">
                        🔍 思考过程 <span class="toggle-icon">▼</span>
                    </div>
                    <div class="thinking-content"></div>
                </div>
                <!-- 正式响应区 -->
                <div class="content-area"></div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageDiv);
        
        // 绑定点击事件
        const header = messageDiv.querySelector('.thinking-header');
        header.onclick = () => this.toggleThinking(header);
        
        this.scrollToBottom();
        return messageDiv;
    }
    
    toggleThinking(header) {
        const container = header.parentElement;
        const content = container.querySelector('.thinking-content');
        const icon = header.querySelector('.toggle-icon');
        
        if (content.style.display === 'none') {
            content.style.display = 'block';
            icon.textContent = '▲';
        } else {
            content.style.display = 'none';
            icon.textContent = '▼';
        }
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        
        // 禁用输入和发送按钮
        this.userInput.disabled = loading;
        this.sendBtn.disabled = loading;
        
        // 禁用快捷按钮
        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.disabled = loading;
            btn.style.opacity = loading ? '0.5' : '1';
            btn.style.cursor = loading ? 'not-allowed' : 'pointer';
        });
        
        // 切换发送/停止按钮
        if (loading) {
            this.sendBtn.innerHTML = '停止';
            this.sendBtn.onclick = () => this.stopGenerating();
        } else {
            this.sendBtn.innerHTML = '发送';
            this.sendBtn.onclick = () => this.sendMessage();
        }
    }
    
    stopGenerating() {
        if (this.abortController) {
            this.abortController.abort();
        }
    }
    
    getHistory() {
        // 获取最近10条历史消息
        return this.messages.slice(-10);
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
}

// 全局切换函数
function toggleThinking(header) {
    const container = header.parentElement;
    const content = container.querySelector('.thinking-content');
    const icon = header.querySelector('.toggle-icon');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.textContent = '▲';
    } else {
        content.style.display = 'none';
        icon.textContent = '▼';
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 初始化markdown-it
    window.md = window.markdownit({
        html: false,
        linkify: true,
        typographer: true
    });
    
    new AnimeChatbot();
});