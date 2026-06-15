# Vendored frontend licenses

These third-party files are checked into `ui/vendor/` so the admin UI runs offline without CDN dependencies. Each entry lists the pinned version, upstream source, and license terms.

---

## Vue.js 2.6.14

| | |
|---|---|
| **File in repo** | `vue.min.js` |
| **Upstream release** | https://github.com/vuejs/vue/releases/tag/v2.6.14 |
| **Source file used** | https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.min.js |
| **License** | MIT |

Copyright (c) 2013-present Yuxi (Evan) You

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## http-vue-loader 1.4.2

| | |
|---|---|
| **File in repo** | `httpVueLoader.min.js` |
| **Upstream release** | https://github.com/FranckFreiburger/http-vue-loader |
| **Version tag** | v1.4.2 |
| **Source file used** | https://cdn.jsdelivr.net/npm/http-vue-loader@1.4.2/src/httpVueLoader.js (minified for repo size) |
| **License** | MIT |

Copyright (c) 2017 Franck Freiburger

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## Refresh procedure

When updating vendored files:

1. Download the new upstream build(s) into `ui/vendor/`.
2. Remove any `sourceMappingURL` comment lines that point at external hosts.
3. Update this file and `README.md` with the new version, URL, and copyright if changed.
4. Run `bash scripts/smoke_test.sh`.
