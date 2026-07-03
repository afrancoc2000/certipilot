// md-to-pdf configuration for the AZ-305 Exam-Day Cheat Sheet.
//
// Usage (run from the repo root so the relative stylesheet path resolves):
//   npx md-to-pdf --config-file data/cheat-sheets/pdf/md-to-pdf.config.js data/cheat-sheets/EXAM-DAY-CHEAT-SHEET.md
//
// Output: data/cheat-sheets/EXAM-DAY-CHEAT-SHEET.pdf
//
// body_class is emptied so md-to-pdf's bundled github-markdown-css (scoped to
// .markdown-body) does not override the bare-element rules in cheat-sheet.css.

module.exports = {
  stylesheet: ["data/cheat-sheets/pdf/cheat-sheet.css"],
  body_class: [],
  pdf_options: {
    format: "A4",
    printBackground: true,
    margin: { top: "12mm", bottom: "14mm", left: "10mm", right: "10mm" },
    displayHeaderFooter: true,
    headerTemplate: "<div></div>",
    footerTemplate:
      '<div style="font-size:8px;width:100%;text-align:center;color:#888;">' +
      'AZ-305 Cheat Sheet &middot; <span class="pageNumber"></span>/<span class="totalPages"></span>' +
      "</div>",
  },
};
