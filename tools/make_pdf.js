/**
 * 把某个页面导出成 A4 PDF，供 tools/check_print.py 检查分页质量。
 *
 *   NODE_PATH=<node-workspace>/node_modules node tools/make_pdf.js <URL> <输出路径>
 *
 * 例子：
 *   node tools/make_pdf.js http://127.0.0.1:4321/sections/02-rocket-tech.html /tmp/p2.pdf
 */
const PW = process.env.PW_PATH || 'playwright';
const { chromium } = require(PW);

const url = process.argv[2];
const out = process.argv[3];
if (!url || !out) {
  console.error('用法：node tools/make_pdf.js <URL> <输出 PDF 路径>');
  process.exit(2);
}

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto(url, { waitUntil: 'load' });
  await p.waitForTimeout(2200);
  // 先滚一遍让进场动效全部触发（打印时 CSS 也会强制显示，但滚动一次更保险）
  await p.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 1200) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 20));
    }
    window.scrollTo(0, 0);
  });
  await p.waitForTimeout(500);
  await p.pdf({ path: out, format: 'A4', printBackground: false,
                margin: { top: '14mm', bottom: '14mm', left: '14mm', right: '14mm' } });
  await b.close();
  console.log('已导出', out);
})();
