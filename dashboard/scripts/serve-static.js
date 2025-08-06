#!/usr/bin/env node

import { createServer } from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = process.env.PORT || 3000;
const BUILD_DIR = path.join(__dirname, '..', 'build', 'client');

// MIME types for different file extensions
const mimeTypes = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.eot': 'application/vnd.ms-fontobject'
};

function getMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  return mimeTypes[ext] || 'application/octet-stream';
}

function serveFile(res, filePath) {
  try {
    const content = fs.readFileSync(filePath);
    const mimeType = getMimeType(filePath);

    res.writeHead(200, {
      'Content-Type': mimeType,
      'Cache-Control': filePath.endsWith('.html') ? 'no-cache' : 'public, max-age=31536000'
    });
    res.end(content);
  } catch (error) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('File not found');
  }
}

function serveIndex(res) {
  const indexPath = path.join(BUILD_DIR, 'index.html');
  if (fs.existsSync(indexPath)) {
    serveFile(res, indexPath);
  } else {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Build not found. Run "npm run build:static" first.');
  }
}

const server = createServer((req, res) => {
  // Add CORS headers for development
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://localhost:${PORT}`);
  let filePath = path.join(BUILD_DIR, url.pathname);

  // Handle root path
  if (url.pathname === '/') {
    serveIndex(res);
    return;
  }

  // Check if file exists
  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    serveFile(res, filePath);
    return;
  }

  // Try to serve with .html extension
  const htmlPath = filePath + '.html';
  if (fs.existsSync(htmlPath)) {
    serveFile(res, htmlPath);
    return;
  }

  // SPA fallback - serve index.html for any route that doesn't exist
  if (!url.pathname.startsWith('/data/') && !url.pathname.includes('.')) {
    serveIndex(res);
    return;
  }

  // File not found
  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not found');
});

server.listen(PORT, () => {
  console.log('🚀 Static server running!');
  console.log(`   Local:    http://localhost:${PORT}`);
  console.log(`   Network:  http://0.0.0.0:${PORT}`);
  console.log(`   Build:    ${BUILD_DIR}`);
  console.log('');
  console.log('📁 Serving static files from build/client');
  console.log('🔄 SPA routing enabled - all routes serve index.html');
  console.log('');
  console.log('Press Ctrl+C to stop');
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n👋 Shutting down static server...');
  server.close(() => {
    console.log('✅ Server closed');
    process.exit(0);
  });
});
