/**
 * 番剧智能助手 - 前端交互脚本
 * 支持 ReAct 动态规划 Agent 的思考过程显示
 */

class AnimeChatbot {
    constructor() {
        this.messagesContainer = document.getElementById('messages');
        this.userInput = document.getElementById('userInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.apiStatus = document.getElementById('apiStatus');
        
        // API 地址
        this.apiBase = 'http://localhost:8000';
        
        // 当前思考步骤
        this.currentThinkingDiv = null;
        
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
            const response = await fetch(`${this.apiBase}/health`, {
                method: 'GET'
            });
            
            if (response.ok) {
                this.apiStatus.textContent = 'API 状态: ✓ 在线';
                this.apiStatus.classList.add('online');
            } else {
                this.apiStatus.textContent = 'API 状态: ✗ 离线';
            }
        } catch (e) {
            this.apiStatus.textContent = 'API 状态: ✗ 离线';
            console.error('API 状态检查失败:', e);
        }
    }
    
    async sendMessage() {
        const message = this.userInput.value.trim();
        if (!message) return;
        
        // 添加用户消息
        this.addMessage(message, 'user');
        this.userInput.value = '';
        
        // 禁用发送按钮
        this.sendBtn.disabled = true;
        
        // 添加机器人消息（流式输出）
        const botMsg = this.addMessage('', 'bot');
        const contentDiv = botMsg.querySelector('.content');
        
        // 使用 SSE 流式接口
        try {
            const response = await fetch(`${this.apiBase}/api/chat/stream`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    query: message,
                    user_id: this.getUserId()
                })
            });
            
            if (!response.ok) {
                throw new Error(`API 请求失败: ${response.status}`);
            }
            
            // 读取流式响应
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                
                // 处理 SSE 格式的数据
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            // 处理不同类型的消息
                            if (data.type === 'thinking') {
                                // 思考过程 - 显示推理步骤
                                this.handleThinking(data, contentDiv);
                            }
                            else if (data.type === 'tool') {
                                // 工具调用
                                this.handleTool(data, contentDiv);
                            }
                            else if (data.type === 'tool_result') {
                                // 工具结果
                                this.handleToolResult(data, contentDiv);
                            }
                            else if (data.type === 'output') {
                                // 最终回复
                                if (data.content) {
                                    contentDiv.innerHTML += data.content.replace(/\n/g, '<br>');
                                    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
                                }
                            }
                            else if (data.type === 'error') {
                                // 错误信息
                                contentDiv.innerHTML += `<br><span style="color: red;">错误: ${data.content}</span>`;
                                this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
                            }
                            else if (data.type === 'done') {
                                // 完成
                                this.sendBtn.disabled = false;
                                this.userInput.focus();
                            }
                            else if (data.content) {
                                // 兼容旧格式
                                contentDiv.innerHTML += data.content.replace(/\n/g, '<br>');
                                this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
                            }
                            
                        } catch (e) {
                            // 忽略解析错误
                        }
                    }
                }
            }
            
        } catch (e) {
            console.error('请求错误:', e);
            contentDiv.innerHTML = `抱歉，服务暂时不可用。<br>错误信息: ${e.message}`;
            this.sendBtn.disabled = false;
            this.userInput.focus();
        }
    }
    
    /**
     * 处理思考过程
     * 显示 LLM 的推理步骤：thought → action → action_input
     */
    handleThinking(data, container) {
        const step = data.step || 1;
        const thought = data.thought || '';
        const action = data.action || '';
        const actionInput = data.action_input || {};
        
        // 创建思考过程显示区域
        let thinkingDiv = container.querySelector('.thinking-process');
        if (!thinkingDiv) {
            thinkingDiv = document.createElement('div');
            thinkingDiv.className = 'thinking-process';
            thinkingDiv.innerHTML = '<div class="thinking-header">🤔 AI 思考过程</div>';
            container.appendChild(thinkingDiv);
        }
        
        // 添加新的思考步骤
        const stepDiv = document.createElement('div');
        stepDiv.className = 'thinking-step';
        
        let actionInputStr = '';
        if (actionInput && Object.keys(actionInput).length > 0) {
            actionInputStr = `<div class="action-input">参数: ${JSON.stringify(actionInput)}</div>`;
        }
        
        stepDiv.innerHTML = `
            <div class="step-title">📝 步骤 ${step}</div>
            <div class="thought">💭 ${this.escapeHtml(thought)}</div>
            ${action ? `<div class="action">⚡ 行动: ${action}</div>` : ''}
            ${actionInputStr}
        `;
        
        thinkingDiv.appendChild(stepDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    /**
     * 处理工具调用
     */
    handleTool(data, container) {
        let toolDiv = container.querySelector('.tool-process');
        if (!toolDiv) {
            toolDiv = document.createElement('div');
            toolDiv.className = 'tool-process';
            toolDiv.innerHTML = '<div class="tool-header">🔧 工具执行</div>';
            container.appendChild(toolDiv);
        }
        
        const toolMsg = document.createElement('div');
        toolMsg.className = 'tool-message';
        toolMsg.innerHTML = this.escapeHtml(data.content || '');
        toolDiv.appendChild(toolMsg);
        
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    /**
     * 处理工具结果
     */
    handleToolResult(data, container) {
        let toolDiv = container.querySelector('.tool-process');
        if (!toolDiv) {
            toolDiv = document.createElement('div');
            toolDiv.className = 'tool-process';
            container.appendChild(toolDiv);
        }
        
        const resultDiv = document.createElement('div');
        resultDiv.className = 'tool-result';
        resultDiv.innerHTML = `<div class="result-label">📊 结果:</div><pre>${this.escapeHtml(data.content || '')}</pre>`;
        toolDiv.appendChild(resultDiv);
        
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    /**
     * HTML 转义
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    addMessage(content, type, isLoading = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}${isLoading ? ' loading' : ''}`;
        
        const avatar = type === 'user' ? '👤' : '🤖';
        
        // 处理内容中的换行
        const formattedContent = content.replace(/\n/g, '<br>');
        
        messageDiv.innerHTML = `
            <div class="avatar">${avatar}</div>
            <div class="content">${formattedContent}</div>
        `;
        
        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        
        return messageDiv;
    }
    
    getUserId() {
        // 生成或获取用户 ID
        let userId = localStorage.getItem('anime_chat_user_id');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('anime_chat_user_id', userId);
        }
        return userId;
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    new AnimeChatbot();
});