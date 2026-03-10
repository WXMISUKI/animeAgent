/**
 * 番剧智能助手 - 前端交互脚本
 */

class AnimeChatbot {
    constructor() {
        this.messagesContainer = document.getElementById('messages');
        this.userInput = document.getElementById('userInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.apiStatus = document.getElementById('apiStatus');
        
        // API 地址
        this.apiBase = 'http://localhost:8000';
        
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
        
        // 添加加载状态
        const loadingMsg = this.addMessage('正在查询番剧信息...', 'bot', true);
        
        try {
            // 调用后端 API
            const response = await fetch(`${this.apiBase}/api/query`, {
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
            
            const data = await response.json();
            
            // 移除加载消息
            loadingMsg.remove();
            
            // 添加回复
            this.addMessage(data.response || data.text || '暂无回复', 'bot');
            
        } catch (e) {
            console.error('请求错误:', e);
            loadingMsg.remove();
            
            // 如果 API 不可用，尝试模拟回复
            this.addMessage(`API 服务暂时不可用，请确保后端服务已启动。\n\n错误信息: ${e.message}`, 'bot');
        } finally {
            // 启用发送按钮
            this.sendBtn.disabled = false;
            this.userInput.focus();
        }
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
