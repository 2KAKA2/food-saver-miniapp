import { defineConfig } from 'vite'
import uniPlugin from '@dcloudio/vite-plugin-uni'

// 当前 Vue3 发行包在较新的 Node.js 中会经过一次 CJS/ESM 互操作包装。
const uni = uniPlugin.default || uniPlugin

export default defineConfig({
  plugins: [uni()],
})
