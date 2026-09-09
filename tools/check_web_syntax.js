const fs = require('fs');

const html = fs.readFileSync('web/index.html', 'utf8');
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
  .map(match => match[1])
  .join('\n');

if (!scripts.trim()) {
  throw new Error('web/index.html contains no executable script');
}

new Function(scripts);
console.log(`web-js-syntax-ok (${scripts.length} characters)`);
