<script setup>
import ChatDialog from './components/ChatDialog.vue'
</script>

<template>
  <div class="app-container">
    <ChatDialog />
    </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  overflow: hidden;
}

#app {
  height: 100vh;
  width: 100vw;
}
</style>

<style scoped>
.app-container {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #e6f3ff 0%, #cce7ff 50%, #b3dcff 100%);
    display: flex;
  flex-direction: column;
}
</style>
