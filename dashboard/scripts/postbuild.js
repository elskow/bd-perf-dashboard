#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const BUILD_DIR = path.join(__dirname, '..', 'build', 'client');
const DATA_SRC = path.join(__dirname, '..', 'public', 'data');
const DATA_DEST = path.join(BUILD_DIR, 'data');

console.log('🔨 Running post-build optimization...\n');

// Copy data files to build directory
function copyDataFiles() {
  console.log('📁 Copying static data files...');

  if (!fs.existsSync(DATA_SRC)) {
    console.warn('⚠️  No data directory found. Run "npm run fetch:data" first.');
    return;
  }

  // Ensure destination directory exists
  if (!fs.existsSync(DATA_DEST)) {
    fs.mkdirSync(DATA_DEST, { recursive: true });
  }

  // Copy all JSON files
  const files = fs.readdirSync(DATA_SRC).filter(file => file.endsWith('.json'));

  files.forEach(file => {
    const src = path.join(DATA_SRC, file);
    const dest = path.join(DATA_DEST, file);
    fs.copyFileSync(src, dest);
    console.log(`  ✓ Copied ${file}`);
  });

  console.log(`📊 Copied ${files.length} data files to build directory`);
}

// Create a manifest file for the static data
function createDataManifest() {
  console.log('\n📋 Creating data manifest...');

  if (!fs.existsSync(DATA_DEST)) {
    console.warn('⚠️  No data files found in build directory');
    return;
  }

  const files = fs.readdirSync(DATA_DEST).filter(file => file.endsWith('.json'));
  const manifest = {
    generated_at: new Date().toISOString(),
    files: files.map(file => {
      const filepath = path.join(DATA_DEST, file);
      const stats = fs.statSync(filepath);
      return {
        name: file,
        size: stats.size,
        modified: stats.mtime.toISOString()
      };
    }),
    total_files: files.length,
    total_size: files.reduce((sum, file) => {
      const filepath = path.join(DATA_DEST, file);
      return sum + fs.statSync(filepath).size;
    }, 0)
  };

  const manifestPath = path.join(DATA_DEST, 'manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  console.log(`  ✓ Created manifest with ${manifest.total_files} files (${(manifest.total_size / 1024).toFixed(1)} KB)`);
}

// Update the index.html to include preload hints
function updateIndexHtml() {
  console.log('\n🔗 Updating index.html with preload hints...');

  const indexPath = path.join(BUILD_DIR, 'index.html');

  if (!fs.existsSync(indexPath)) {
    console.warn('⚠️  index.html not found in build directory');
    return;
  }

  let html = fs.readFileSync(indexPath, 'utf-8');

  // Add preload hints for critical data files
  const preloadHints = [
    '<link rel="preload" href="/data/sales-teams.json" as="fetch" crossorigin>',
    '<link rel="preload" href="/data/all-dashboards.json" as="fetch" crossorigin>',
    '<link rel="preload" href="/data/metadata.json" as="fetch" crossorigin>'
  ];

  // Insert preload hints before closing head tag
  const headCloseIndex = html.indexOf('</head>');
  if (headCloseIndex !== -1) {
    const beforeHead = html.substring(0, headCloseIndex);
    const afterHead = html.substring(headCloseIndex);
    html = beforeHead + '  ' + preloadHints.join('\n  ') + '\n' + afterHead;

    fs.writeFileSync(indexPath, html);
    console.log('  ✓ Added preload hints to index.html');
  }
}

// Create a simple 404.html for GitHub Pages and similar static hosts
function create404Page() {
  console.log('\n📄 Creating 404.html for static hosting...');

  const indexPath = path.join(BUILD_DIR, 'index.html');
  const notFoundPath = path.join(BUILD_DIR, '404.html');

  if (fs.existsSync(indexPath)) {
    fs.copyFileSync(indexPath, notFoundPath);
    console.log('  ✓ Created 404.html (copy of index.html for SPA routing)');
  }
}

// Create a _redirects file for Netlify
function createRedirectsFile() {
  console.log('\n🔀 Creating _redirects for Netlify...');

  const redirectsContent = `# Netlify redirects for SPA
/*    /index.html   200

# API fallback (if needed)
/api/*  https://your-api-domain.com/api/:splat  200
`;

  const redirectsPath = path.join(BUILD_DIR, '_redirects');
  fs.writeFileSync(redirectsPath, redirectsContent);
  console.log('  ✓ Created _redirects file for Netlify');
}

// Main execution
function main() {
  try {
    copyDataFiles();
    createDataManifest();
    updateIndexHtml();
    create404Page();
    createRedirectsFile();

    console.log('\n🎉 Post-build optimization completed successfully!');
    console.log('\n📁 Build output:');
    console.log(`   ${BUILD_DIR}`);
    console.log('\n🚀 Ready for static deployment!');
    console.log('\nDeployment options:');
    console.log('  • GitHub Pages: Upload build/client folder');
    console.log('  • Netlify: Deploy build/client folder');
    console.log('  • Vercel: Deploy build/client folder');
    console.log('  • Local serve: npm run serve:static');

  } catch (error) {
    console.error('\n❌ Post-build optimization failed:', error.message);
    process.exit(1);
  }
}

main();
