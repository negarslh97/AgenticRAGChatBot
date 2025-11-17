#!/usr/bin/env node

/**
 * اسکریپت برای راه‌اندازی توسعه محلی با تنظیمات API
 * 
 * نحوه استفاده:
 * - برای توسعه محلی: npm run start-dev
 * - برای اتصال به سرور: API_TARGET=192.168.10.221:8000 npm run start-dev
 */

const { spawn } = require('child_process');
const dotenv = require('dotenv');

// بارگذاری متغیرهای محیطی
dotenv.config();

const API_TARGET = process.env.API_TARGET || 'localhost:8000';
const PORT = process.env.PORT || 3000;

console.log(`🚀 Starting frontend development server...`);
console.log(`🎯 API Target: ${API_TARGET}`);
console.log(`🌐 Frontend Port: ${PORT}`);

// تنظیم متغیر محیطی برای proxy
process.env.API_TARGET = API_TARGET;

// راه‌اندازی سرور توسعه
const reactScripts = spawn('node', ['node_modules/react-scripts/bin/react-scripts.js', 'start'], {
  stdio: 'inherit',
  env: { ...process.env, PORT: PORT.toString(), API_TARGET: API_TARGET }
});

reactScripts.on('close', (code) => {
  console.log(`\n🛑 Frontend development server stopped with code ${code}`);
  process.exit(code);
});

reactScripts.on('error', (error) => {
  console.error('❌ Failed to start frontend development server:', error);
  process.exit(1);
});