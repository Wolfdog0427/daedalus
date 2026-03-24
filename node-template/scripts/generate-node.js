#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const name = process.argv[2];
if (!name) {
  console.error('Usage: node generate-node.js <node-name>');
  console.error('Example: node generate-node.js node-desktop-01');
  process.exit(1);
}

const templateDir = path.resolve(__dirname, '..');
const targetDir = path.resolve(process.cwd(), name);

if (fs.existsSync(targetDir)) {
  console.error(`Directory already exists: ${targetDir}`);
  process.exit(1);
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.name === 'node_modules' || entry.name === 'dist') continue;
    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

copyDir(templateDir, targetDir);

const pkgPath = path.join(targetDir, 'package.json');
if (fs.existsSync(pkgPath)) {
  const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
  pkg.name = `@daedalus/${name}`;
  fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n');
}

console.log(`Node package created: ${targetDir}`);
console.log(`  Name: @daedalus/${name}`);
console.log('');
console.log('Next steps:');
console.log(`  1. cd ${name}`);
console.log('  2. npm install');
console.log('  3. Customize src/adapters/ for your platform');
console.log('  4. npm test');
