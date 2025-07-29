<template>
  <div class="chat-container">
    <!-- 顶部标题区 -->
    <div class="chat-header">
      <div class="header-content">
        <h1 class="title">AI 聊天助手</h1>
      </div>
    </div>

    <!-- MCP 配置弹窗 -->
    <el-dialog 
      v-model="showMcpConfigModal" 
      title="MCP工具配置" 
      width="80%"
      :before-close="handleMcpConfigClose"
      class="mcp-config-dialog"
    >
      <div class="mcp-config-content">
        <div v-for="option in mcpOptions" :key="option.value" class="mcp-config-item">
          <div class="mcp-header">
            <div class="mcp-info">
              <h3 class="mcp-title">{{ option.label }}</h3>
              <p class="mcp-description">{{ option.description }}</p>
              <div v-if="option.mcp_url" class="mcp-url">
                <el-tag size="small" type="info">外部MCP: {{ option.mcp_url }}</el-tag>
              </div>
            </div>
            <div class="mcp-control">
              <el-switch
                v-model="mcpSwitchStates[option.value]"
                @change="handleMcpSwitch(option.value, $event)"
                size="large"
                active-text="启用"
                inactive-text="禁用"
              />
            </div>
          </div>
          
          <div v-if="mcpSwitchStates[option.value]" class="mcp-tools-section">
            <div class="tools-header">
              <h4>可用工具</h4>
              <el-button 
                @click="loadMcpTools(option)" 
                :icon="Refresh"
                size="small"
                type="primary"
                text
                :loading="loadingMcpTools[option.value]"
              >
                刷新
              </el-button>
            </div>
            <div class="tools-content">
              <div v-if="loadingMcpTools[option.value]" class="loading-tools">
                <el-skeleton :rows="3" animated />
              </div>
              <div v-else-if="mcpToolsData[option.value]?.length === 0" class="no-tools">
                <el-empty description="暂无可用工具" :image-size="60" />
              </div>
              <div v-else class="tools-grid">
                <div 
                  v-for="tool in mcpToolsData[option.value]" 
                  :key="tool.name" 
                  class="tool-card"
                >
                  <div class="tool-header">
                    <h5 class="tool-name">{{ tool.name }}</h5>
                    <el-tag size="small" type="success">工具</el-tag>
                  </div>
                  <p class="tool-description">{{ tool.description }}</p>
                  <div v-if="tool.parameters" class="tool-params">
                    <el-collapse size="small">
                      <el-collapse-item title="参数详情" name="params">
                        <pre class="params-code">{{ JSON.stringify(tool.parameters, null, 2) }}</pre>
                      </el-collapse-item>
                    </el-collapse>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showMcpConfigModal = false">取消</el-button>
          <el-button type="primary" @click="saveMcpConfig">保存配置</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 聊天消息区域 -->
    <div class="chat-messages-outer">
      <div class="chat-messages" ref="messagesRef">
        <div class="messages-wrapper">
          <div v-for="(msg, idx) in messages" :key="idx" :class="['message-row', msg.role]">
            <div class="chat-bubble">
              <div class="bubble-content" v-if="msg.role === 'ai'" v-html="renderMarkdown(msg.content)"></div>
              <div class="bubble-content" v-else>{{ msg.content }}</div>
            </div>
          </div>
          <!-- 打字机效果显示区 -->
          <div v-if="isTyping" class="message-row ai">
            <div class="chat-bubble typing">
              <div class="bubble-content" v-html="renderMarkdown(typingContent)"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部输入区 -->
    <div class="chat-input-area-outer">
      <div class="chat-input-area">
        <!-- 选择器区域 -->
        <div class="controls-row">
          <div class="mcp-selector">
            <label class="selector-label">MCP工具:</label>
            <div class="mcp-select-wrapper">
              <el-button
                @click="openMcpConfig"
                :icon="Setting"
                size="default"
                type="primary"
                class="mcp-config-btn"
              >
                配置MCP ({{ selectedMcp.length }})
              </el-button>
              <div class="selected-mcp-tags">
                <el-tag
                  v-for="mcpValue in selectedMcp"
                  :key="mcpValue"
                  closable
                  @close="removeMcp(mcpValue)"
                  size="small"
                  type="primary"
                >
                  {{ mcpOptions.find(opt => opt.value === mcpValue)?.label }}
                </el-tag>
              </div>
            </div>
          </div>
          <div class="model-selector">
            <label class="selector-label">模型:</label>
            <el-select
              v-model="selectedModel"
              placeholder="请选择模型"
              class="model-select-mini"
              size="default"
              clearable
            >
              <el-option
                v-for="model in availableModels"
                :key="model.name"
                :label="model.name + (!model.available ? ' (不可用)' : '')"
                :value="model.name"
                :disabled="!model.available"
              />
            </el-select>
          </div>
        </div>
        
        <!-- 输入框区域 -->
        <form class="input-form" @submit.prevent="sendMessage">
          <div class="input-wrapper">
            <input 
              v-model="input" 
              type="text" 
              placeholder="请输入你的问题..." 
              :disabled="loading"
              class="message-input"
            />
            <button type="submit" :disabled="!input || loading" class="send-button">
              {{ loading ? '发送中...' : '发送' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onMounted, watch } from 'vue';
import { marked } from 'marked';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';
import { Setting, Refresh } from '@element-plus/icons-vue';

const API_BASE = 'http://localhost:8000';

// 状态管理
const mcpOptions = ref([]);
const availableModels = ref([]);
const selectedMcp = ref([]);
const selectedModel = ref('');
const input = ref('');
const loading = ref(false);
const isTyping = ref(false);
const typingContent = ref('');
// 展示用 role: user/ai，发给后端时 role: user/assistant
const messages = reactive([
  { role: 'ai', content: '你好！我是AI助手，有什么可以帮助您的吗？' }
]);
const messagesRef = ref(null);
const showMcpConfigModal = ref(false);
const mcpSwitchStates = ref({});
const mcpToolsData = ref({});
const loadingMcpTools = ref({});

onMounted(async () => {
  await loadConfig();
  
  // 配置marked使用highlight.js进行代码高亮
  marked.setOptions({
    highlight: function(code, lang) {
      // 语言别名映射
      const languageAliases = {
        'js': 'javascript',
        'ts': 'typescript',
        'py': 'python',
        'sh': 'bash',
        'yml': 'yaml',
        'md': 'markdown'
      };
      
      // 如果没有指定语言，尝试自动检测
      if (!lang) {
        // 尝试自动检测JSON格式
        try {
          JSON.parse(code);
          lang = 'json';
        } catch (e) {
          // 如果不是JSON，使用自动检测
          const detected = hljs.highlightAuto(code);
          return detected.value;
        }
      }
      
      // 处理语言别名
      const normalizedLang = languageAliases[lang] || lang;
      
      // 检查语言是否被支持
      if (hljs.getLanguage(normalizedLang)) {
        try {
          return hljs.highlight(code, { language: normalizedLang }).value;
        } catch (e) {
          console.warn('Highlight.js error:', e);
          return hljs.highlightAuto(code).value;
        }
      } else {
        // 如果语言不被支持，使用自动检测
        return hljs.highlightAuto(code).value;
      }
    },
    langPrefix: 'hljs language-'
  });
});

const loadConfig = async () => {
  try {
    const response = await fetch(`${API_BASE}/config`);
    const config = await response.json();
    
    mcpOptions.value = config.mcp_options || [];
    availableModels.value = config.available_models || [];
    selectedModel.value = config.default_model || '';
    
    // 初始化MCP状态
    initializeMcpStates();
    
    // 默认选择第一个MCP
    if (mcpOptions.value.length > 0) {
      selectedMcp.value = [mcpOptions.value[0].value];
    }
  } catch (error) {
    console.error('加载配置失败:', error);
    mcpOptions.value = [
      { label: '数据查询', value: 'data_query', description: '企业数据查询和统计功能' },
      { label: '文件处理', value: 'file_processing', description: '文件上传、处理和分析功能' }
    ];
    availableModels.value = [
      { name: 'GPT-3.5 Turbo', available: false }
    ];
    selectedModel.value = 'GPT-3.5 Turbo';
    
    // 初始化MCP状态
    initializeMcpStates();
    
    // 默认选择第一个MCP
    if (mcpOptions.value.length > 0) {
      selectedMcp.value = [mcpOptions.value[0].value];
    }
  }
};

// MCP配置相关函数
const initializeMcpStates = () => {
  mcpSwitchStates.value = {};
  mcpToolsData.value = {};
  loadingMcpTools.value = {};
  
  mcpOptions.value.forEach((option, index) => {
    // 根据selectedMcp来设置开关状态
    mcpSwitchStates.value[option.value] = selectedMcp.value.includes(option.value);
    mcpToolsData.value[option.value] = [];
    loadingMcpTools.value[option.value] = false;
  });
};

const handleMcpSwitch = (mcpValue, enabled) => {
  console.log(`MCP开关变化: ${mcpValue} = ${enabled}`);
  
  if (enabled) {
    // 启用MCP
    if (!selectedMcp.value.includes(mcpValue)) {
      selectedMcp.value.push(mcpValue);
      console.log(`添加MCP到选中列表: ${mcpValue}`);
    }
    // 自动加载工具
    const mcpOption = mcpOptions.value.find(opt => opt.value === mcpValue);
    if (mcpOption) {
      console.log(`开关启用，开始加载工具: ${mcpOption.label}`);
      loadMcpTools(mcpOption);
    }
  } else {
    // 禁用MCP
    console.log(`开关禁用，移除MCP: ${mcpValue}`);
    removeMcp(mcpValue);
  }
};

const loadMcpTools = async (mcpOption) => {
  console.log(`开始加载 ${mcpOption.label} 的工具...`);
  loadingMcpTools.value[mcpOption.value] = true;
  
  try {
    const response = await fetch(`${API_BASE}/mcp/${mcpOption.value}/tools`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    mcpToolsData.value[mcpOption.value] = data.tools || [];
    console.log(`成功加载 ${mcpOption.label} 的 ${mcpToolsData.value[mcpOption.value].length} 个工具`);
  } catch (error) {
    console.error(`获取${mcpOption.label}工具失败:`, error);
    mcpToolsData.value[mcpOption.value] = [];
  } finally {
    loadingMcpTools.value[mcpOption.value] = false;
  }
};

const removeMcp = (mcpValue) => {
  const index = selectedMcp.value.indexOf(mcpValue);
  if (index > -1) {
    selectedMcp.value.splice(index, 1);
  }
  mcpSwitchStates.value[mcpValue] = false;
};

const handleMcpConfigClose = (done) => {
  // 这里可以添加确认逻辑
  done();
};

const openMcpConfig = async () => {
  showMcpConfigModal.value = true;
  
  // 确保开关状态与selectedMcp同步
  mcpOptions.value.forEach(option => {
    mcpSwitchStates.value[option.value] = selectedMcp.value.includes(option.value);
  });
  
  // 为所有已启用的MCP并发加载工具（如果还没有加载的话）
  const loadPromises = [];
  for (const mcpValue of selectedMcp.value) {
    const mcpOption = mcpOptions.value.find(opt => opt.value === mcpValue);
    // 如果工具数据为空或者从未加载过，则加载工具
    if (mcpOption && (!mcpToolsData.value[mcpValue] || mcpToolsData.value[mcpValue].length === 0)) {
      console.log(`准备加载 ${mcpOption.label} 的工具...`);
      loadPromises.push(loadMcpTools(mcpOption));
    }
  }
  
  // 等待所有工具加载完成
  if (loadPromises.length > 0) {
    console.log(`正在并发加载 ${loadPromises.length} 个MCP的工具...`);
    await Promise.all(loadPromises);
    console.log('所有MCP工具加载完成');
  }
};

const saveMcpConfig = () => {
  // 保存配置到本地存储或发送到服务器
  console.log('保存MCP配置:', {
    selectedMcp: selectedMcp.value,
    switchStates: mcpSwitchStates.value
  });
  showMcpConfigModal.value = false;
};

const sendMessage = async () => {
  if (!input.value.trim()) return;
  
  const userMessage = input.value;
  messages.push({ role: 'user', content: userMessage });
  loading.value = true;
  input.value = '';
  
  await nextTick();
  scrollToBottom();
  
  try {
    await sendStreamingMessage(userMessage);
  } catch (error) {
    console.error('发送消息失败:', error);
    messages.push({ 
      role: 'ai', 
      content: '抱歉，发送消息时出现错误，请稍后重试。'
    });
  } finally {
    loading.value = false;
    isTyping.value = false;
    typingContent.value = '';
  }
};

function toApiMessages(messages) {
  // user => user, ai => assistant
  return messages
    .filter(msg => !msg.typing)
    .map(msg => ({
      role: msg.role === 'ai' ? 'assistant' : msg.role,
      content: msg.content
    }));
}

const sendStreamingMessage = async (userMessage) => {
  try {
    const requestBody = {
      messages: toApiMessages(messages),
      selected_mcp: selectedMcp.value,
      model: selectedModel.value
    };

    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    isTyping.value = true;
    typingContent.value = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            
            if (data.type === 'start') {
              console.log('开始接收流式响应:', data);
            } else if (data.type === 'chunk') {
              typingContent.value += data.content;
              await nextTick();
              scrollToBottom();
            } else if (data.type === 'error') {
              console.error('流式响应错误:', data);
              // 显示错误信息
              typingContent.value += `\n\n❌ ${data.content}`;
              await nextTick();
              scrollToBottom();
            } else if (data.type === 'end') {
              console.log('流式响应结束:', data);
              if (typingContent.value) {
                messages.push({ 
                  role: 'ai', 
                  content: typingContent.value 
                });
              }
              isTyping.value = false;
              typingContent.value = '';
              await nextTick();
              scrollToBottom();
              break;
            }
          } catch (parseError) {
            console.error('解析SSE数据失败:', parseError);
          }
        }
      }
    }
  } catch (error) {
    console.error('流式请求失败:', error);
    await sendNormalMessage(userMessage);
  }
};

const sendNormalMessage = async (userMessage) => {
  try {
    const requestBody = {
      messages: toApiMessages(messages),
      selected_mcp: selectedMcp.value,
      model: selectedModel.value
    };

    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    messages.push({ 
      role: 'ai', 
      content: result.message 
    });
    
    await nextTick();
    scrollToBottom();
  } catch (error) {
    console.error('普通请求失败:', error);
    throw error;
  }
};

function scrollToBottom(force = false) {
  if (messagesRef.value) {
    // 兼容 sticky 输入区，强制滚动到底部
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight;
    // 某些浏览器下 sticky 可能导致未滚动到底，强制多滚一次
    if (force) {
      setTimeout(() => {
        messagesRef.value.scrollTop = messagesRef.value.scrollHeight;
      }, 50);
    }
  }
}

// 自动滚动到底部：监听消息和打字机内容
watch(
  () => [messages.length, isTyping.value, typingContent.value],
  async () => {
    await nextTick();
    scrollToBottom(true);
  }
);

function renderMarkdown(text) {
  return marked.parse(text || '');
}


</script>

<style scoped>
.chat-container {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #e6f3ff 0%, #cce7ff 50%, #b3dcff 100%);
  display: flex;
  flex-direction: column;
  /* 弹性布局：头部、聊天区、输入区 */
}

/* 头部固定高度 */
.chat-header {
  width: 100vw;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(240, 248, 255, 0.95) 100%);
  border-bottom: 3px solid #b3dcff;
  box-shadow: 0 4px 20px rgba(51, 128, 197, 0.12);
  padding: 0;
  /* 固定高度，不参与弹性伸缩 */
  flex-shrink: 0;
  min-height: 80px; /* 减小高度 */
  backdrop-filter: blur(10px);
  position: relative;
}

.chat-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(77, 166, 255, 0.3), transparent);
}

.header-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px 24px;
}

.title {
  font-size: 2.2rem;
  color: #2c5aa0;
  font-weight: 800;
  margin: 0;
  text-align: center;
  text-shadow: 0 2px 4px rgba(44, 90, 160, 0.1);
  background: linear-gradient(135deg, #2c5aa0 0%, #4da6ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 中间聊天记录区域 - 弹性伸缩 */
.chat-messages-outer {
  width: 100vw;
  display: flex;
  justify-content: center;
  background: transparent;
  /* 弹性伸缩：占满剩余空间 */
  flex: 1;
  min-height: 0; /* 重要：允许flex子元素收缩 */
  overflow: hidden;
}

.chat-messages {
  width: 100%;
  max-width: 900px;
  height: 100%;
  overflow-y: auto;
  padding: 20px 20px 0 20px;
  background: transparent;
  display: flex;
  flex-direction: column;
  /* 始终显示滚动条 */
  scrollbar-gutter: stable both-edges;
}

/* 始终显示滚动条（兼容主流浏览器） */
.chat-messages {
  scrollbar-width: thin;
  scrollbar-color: #b3dcff #f0f8ff;
}
.chat-messages::-webkit-scrollbar {
  width: 8px;
}
.chat-messages::-webkit-scrollbar-track {
  background: #f0f8ff;
  border-radius: 4px;
}
.chat-messages::-webkit-scrollbar-thumb {
  background: #b3dcff;
  border-radius: 4px;
}
.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #99d6ff;
}

.messages-wrapper {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  /* 增加底部空间，避免最后一条消息贴边 */
  padding-bottom: 40px;
}

.message-row {
  display: flex;
  width: 100%;
}
.message-row.user {
  justify-content: flex-end;
}
.message-row.ai {
  justify-content: flex-start;
}

.chat-bubble {
  min-width: 80px;
}
.message-row.user .chat-bubble {
  background: linear-gradient(135deg, #4da6ff 0%, #0066cc 100%);
  color: white;
  border-radius: 18px 18px 6px 18px;
  max-width: 70%;
}
.message-row.ai .chat-bubble {
  background: rgba(255, 255, 255, 0.98);
  color: #2c5aa0;
  border: 1.5px solid #e6f3ff;
  border-radius: 18px 18px 18px 6px;
  max-width: 100%;
}
.chat-bubble.typing {
  background: rgba(255, 255, 255, 0.98);
  border: 1.5px solid #99d6ff;
  animation: pulse 1.5s infinite;
  max-width: 100%;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
.bubble-content {
  padding: 14px 18px;
  font-size: 1.08rem;
  line-height: 1.6;
  word-wrap: break-word;
}

/* 代码块样式优化 */
.bubble-content :deep(pre) {
  background: #f8f9fa !important;
  border: 1px solid #e6f3ff;
  border-radius: 8px;
  padding: 16px;
  margin: 12px 0;
  overflow-x: auto;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.9em;
  line-height: 1.5;
  box-shadow: 0 2px 4px rgba(51, 128, 197, 0.1);
}

.bubble-content :deep(code) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.9em;
}

/* 内联代码样式 */
.bubble-content :deep(p code) {
  background: #f0f8ff;
  border: 1px solid #cce7ff;
  border-radius: 4px;
  padding: 2px 6px;
  margin: 0 2px;
  color: #c7254e;
  font-weight: 500;
}

/* 代码块复制按钮区域 */
.bubble-content :deep(pre) {
  position: relative;
}

/* 为AI消息的代码块优化颜色 */
.message-row.ai .bubble-content :deep(pre) {
  background: #f8f9fa !important;
  border-color: #e6f3ff;
}

/* 为用户消息的代码块优化颜色 */
.message-row.user .bubble-content :deep(pre) {
  background: rgba(255, 255, 255, 0.15) !important;
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
}

.message-row.user .bubble-content :deep(code) {
  color: inherit;
}

.message-row.user .bubble-content :deep(p code) {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
}

/* 确保语法高亮在白色背景上可见 */
.bubble-content :deep(.hljs) {
  background: #f8f9fa !important;
  color: #24292e;
}

/* 调整部分语法高亮颜色以提高对比度 */
.bubble-content :deep(.hljs-comment),
.bubble-content :deep(.hljs-quote) {
  color: #6a737d;
  font-style: italic;
}

.bubble-content :deep(.hljs-keyword),
.bubble-content :deep(.hljs-selector-tag),
.bubble-content :deep(.hljs-type) {
  color: #d73a49;
  font-weight: 600;
}

.bubble-content :deep(.hljs-string),
.bubble-content :deep(.hljs-attr) {
  color: #032f62;
}

.bubble-content :deep(.hljs-number),
.bubble-content :deep(.hljs-literal) {
  color: #005cc5;
}

.bubble-content :deep(.hljs-function),
.bubble-content :deep(.hljs-title) {
  color: #6f42c1;
  font-weight: 600;
}

/* JSON特定样式优化 */
.bubble-content :deep(.hljs-attr) {
  color: #005cc5;
  font-weight: 600;
}

.bubble-content :deep(.hljs-string) {
  color: #032f62;
}

.bubble-content :deep(.hljs-number) {
  color: #e36209;
  font-weight: 500;
}

.bubble-content :deep(.hljs-literal) {
  color: #d73a49;
  font-weight: 600;
}

/* JSON的键名高亮 */
.bubble-content :deep(.hljs-attr)::before {
  content: '';
}

/* 增强JSON可读性 */
.bubble-content :deep(.language-json .hljs-punctuation) {
  color: #6a737d;
  font-weight: 500;
}

/* 底部输入区 - 固定高度 */
.chat-input-area-outer {
  width: 100vw;
  display: flex;
  justify-content: center;
  background: transparent;
  /* 固定高度，不参与弹性伸缩 */
  flex-shrink: 0;
  min-height: 120px; /* 增加高度以容纳控制区域 */
}

.chat-input-area {
  width: 100%;
  max-width: 900px;
  background: rgba(255,255,255,0.98);
  border-top: 2px solid #b3dcff;
  box-shadow: 0 -2px 10px rgba(51, 128, 197, 0.08);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 控制区域样式 */
.controls-row {
  display: flex;
  gap: 20px;
  align-items: center;
  flex-wrap: wrap;
  padding: 12px 16px;
  background: linear-gradient(135deg, #f8fbff 0%, #f0f8ff 100%);
  border-radius: 12px;
  border: 1px solid #e6f3ff;
  box-shadow: 0 2px 6px rgba(51, 128, 197, 0.08);
}

.mcp-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 250px;
}

.model-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 180px;
}

.selector-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #2c5aa0;
  min-width: fit-content;
}

.mcp-select-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  position: relative;
}

/* Element Plus 组件自定义样式 */
.model-select-mini {
  min-width: 160px;
}

/* 自定义 Element Plus select 样式 - 优化清晰度 */

.model-select-mini :deep(.el-select__wrapper) {
  border: 2px solid #e6f3ff;
  border-radius: 12px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 2px 8px rgba(51, 128, 197, 0.08);
  transition: all 0.3s ease;
  padding: 8px 12px;
  /* 文字清晰度优化 */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  transform: translateZ(0);
  backface-visibility: hidden;
}

.model-select-mini :deep(.el-select__wrapper:hover) {
  border-color: #99d6ff;
  background: linear-gradient(135deg, #f8fbff 0%, #e6f3ff 100%);
  transform: translateY(-1px) translateZ(0);
}

.model-select-mini :deep(.el-select__wrapper.is-focused) {
  border-color: #4da6ff;
  box-shadow: 0 0 0 4px rgba(77, 166, 255, 0.15);
  transform: translateZ(0);
}

/* 下拉面板样式 - 优化清晰度 */

.model-select-mini :deep(.el-select-dropdown) {
  border: 2px solid #e6f3ff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(51, 128, 197, 0.15);
  /* 文字清晰度优化 */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  transform: translateZ(0);
}



/* Element Plus 按钮样式优化 - 解决模糊问题 */
.mcp-select-wrapper :deep(.el-button.is-circle) {
  background: linear-gradient(135deg, #4da6ff 0%, #0066cc 100%);
  border: 2px solid #4da6ff;
  box-shadow: 0 2px 8px rgba(77, 166, 255, 0.3);
  transition: all 0.3s ease;
  /* 优化字体渲染和清晰度 */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  /* 确保像素对齐 */
  transform: translateZ(0);
  will-change: transform;
  /* 防止模糊 */
  backface-visibility: hidden;
  perspective: 1000px;
}

.mcp-select-wrapper :deep(.el-button.is-circle .el-icon) {
  /* 图标清晰度优化 */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  transform: translateZ(0);
}

.mcp-select-wrapper :deep(.el-button.is-circle:hover) {
  background: linear-gradient(135deg, #3399ff 0%, #0052a3 100%);
  border-color: #3399ff;
  transform: translateY(-1px) translateZ(0);
  box-shadow: 0 4px 12px rgba(77, 166, 255, 0.4);
}

.mcp-select-wrapper :deep(.el-button.is-circle:active) {
  transform: translateY(0) translateZ(0);
}

.input-form {
  width: 100%;
  margin: 0;
}

.input-wrapper {
  display: flex;
  gap: 14px;
  align-items: center;
}

.message-input {
  flex: 1;
  padding: 14px 18px;
  border: 1.5px solid #cce7ff;
  border-radius: 10px;
  font-size: 1.08rem;
  background: white;
  outline: none;
  transition: border-color 0.2s;
}
.message-input:focus {
  border-color: #4da6ff;
  box-shadow: 0 0 0 2px rgba(77, 166, 255, 0.08);
}
.message-input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.send-button {
  padding: 14px 28px;
  background: linear-gradient(135deg, #4da6ff 0%, #0066cc 100%);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 1.08rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 100px;
}
.send-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #3399ff 0%, #0052a3 100%);
  transform: translateY(-1px);
}
.send-button:disabled {
  background: #cccccc;
  cursor: not-allowed;
  transform: none;
}

/* 模态框样式保持不变 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 600px;
  max-height: 80vh;
  width: 90vw;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e6f3ff;
}

.modal-header h3 {
  margin: 0;
  color: #2c5aa0;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.modal-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid #e6f3ff;
}

.mcp-info {
  background: #f0f8ff;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.tool-item {
  border: 1px solid #e6f3ff;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}

.tool-item h4 {
  margin: 0 0 8px 0;
  color: #2c5aa0;
}

.tool-item p {
  margin: 0 0 12px 0;
  color: #666;
}

.tool-params {
  background: #f8f9fa;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
}

.tool-params pre {
  margin: 4px 0 0 0;
  overflow-x: auto;
}

.loading, .no-tools {
  text-align: center;
  color: #666;
  padding: 40px;
}

.refresh-btn {
  background: linear-gradient(135deg, #4da6ff 0%, #0066cc 100%);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  cursor: pointer;
}

.close-btn {
  background: #f5f5f5;
  color: #666;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 8px 16px;
  cursor: pointer;
}

/* MCP配置弹窗样式 */
.selected-mcp-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 8px;
}

.mcp-config-btn {
  min-width: 140px;
}

/* MCP配置对话框样式 */
.mcp-config-dialog :deep(.el-dialog) {
  border-radius: 16px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
}

.mcp-config-dialog :deep(.el-dialog__header) {
  background: linear-gradient(135deg, #4da6ff 0%, #0066cc 100%);
  color: white;
  border-radius: 16px 16px 0 0;
  padding: 20px 24px;
}

.mcp-config-dialog :deep(.el-dialog__title) {
  color: white;
  font-weight: 600;
}

.mcp-config-content {
  max-height: 60vh;
  overflow-y: auto;
  padding: 20px;
}

.mcp-config-item {
  margin-bottom: 24px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  border: 2px solid #e6f3ff;
  box-shadow: 0 2px 8px rgba(51, 128, 197, 0.08);
  transition: all 0.3s ease;
}

.mcp-config-item:hover {
  border-color: #99d6ff;
  box-shadow: 0 4px 16px rgba(51, 128, 197, 0.12);
}

.mcp-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.mcp-info {
  flex: 1;
}

.mcp-title {
  margin: 0 0 8px 0;
  color: #2c5aa0;
  font-size: 1.2rem;
  font-weight: 600;
}

.mcp-description {
  margin: 0 0 8px 0;
  color: #6b7280;
  line-height: 1.4;
}

.mcp-url {
  margin-top: 8px;
}

.mcp-control {
  margin-left: 20px;
}

.mcp-tools-section {
  border-top: 1px solid #e6f3ff;
  padding-top: 16px;
  margin-top: 16px;
}

.tools-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.tools-header h4 {
  margin: 0;
  color: #2c5aa0;
  font-size: 1rem;
  font-weight: 600;
}

.tools-content {
  background: #f8fbff;
  border-radius: 8px;
  padding: 16px;
}

.loading-tools,
.no-tools {
  text-align: center;
  padding: 20px;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.tool-card {
  background: white;
  border: 1px solid #e6f3ff;
  border-radius: 8px;
  padding: 12px;
  transition: all 0.2s ease;
}

.tool-card:hover {
  border-color: #99d6ff;
  box-shadow: 0 2px 8px rgba(51, 128, 197, 0.1);
}

.tool-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.tool-name {
  margin: 0;
  color: #2c5aa0;
  font-size: 0.9rem;
  font-weight: 600;
}

.tool-description {
  margin: 0 0 8px 0;
  color: #6b7280;
  font-size: 0.85rem;
  line-height: 1.3;
}

.tool-params {
  margin-top: 8px;
}

.params-code {
  font-size: 0.75rem;
  line-height: 1.2;
  max-height: 120px;
  overflow-y: auto;
  background: #f8f9fa;
  padding: 8px;
  border-radius: 4px;
  margin: 0;
}

.dialog-footer {
  padding: 16px 24px;
  text-align: right;
  background: #f8fbff;
  border-radius: 0 0 16px 16px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .controls-row {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .mcp-selector, .model-selector {
    justify-content: space-between;
    width: 100%;
    min-width: auto;
  }
  
  .mcp-select-wrapper {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    min-width: auto;
  }
  
  .mcp-config-btn {
    min-width: auto;
    width: 100%;
  }
  
  .selected-mcp-tags {
    justify-content: flex-start;
  }
  
  .tools-grid {
    grid-template-columns: 1fr;
  }
  
  .mcp-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .mcp-control {
    margin-left: 0;
    text-align: center;
  }
  
  .model-select-mini {
    min-width: 120px;
  }
  
  .title {
    font-size: 1.8rem;
  }
  
  .chat-header {
    min-height: 70px;
  }
  
  .header-content {
    padding: 16px 20px;
  }
}

/* 全局 Element Plus 组件清晰度优化 */
:deep(.el-select__wrapper),
:deep(.el-select-dropdown),
:deep(.el-option),
:deep(.el-tag),
:deep(.el-button) {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

/* 全局文字和图标清晰度 */
:deep(.el-icon),
:deep(.el-select__caret),
:deep(.el-tag__close) {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  transform: translateZ(0);
}

/* 防止动画模糊 */
:deep(.el-select__wrapper),
:deep(.el-button) {
  will-change: auto;
  backface-visibility: hidden;
  perspective: 1000px;
}
</style> 