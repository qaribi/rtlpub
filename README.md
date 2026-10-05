# rtlpub

Offline, read-only publishing preflight for Persian and right-to-left content.
Check UTF-8 text, XML-based XHTML and unencrypted EPUB 3 publications. Findings
help authors inspect Unicode, language/direction, basic accessibility and broken
publication references before handing a book to a reading system.

rtlpub complements [EPUBCheck](https://github.com/w3c/epubcheck) and
[Ace by DAISY](https://github.com/daisy/ace). It is a small set of checks, not an
EPUB conformance certificate, accessibility certification or linguistic proofreader.
This is a new project; external adoption and a long-term maintenance record are
not established.

## Install and run

Python 3.12 or newer is required. There are no third-party runtime dependencies.
From a checkout:

~~~sh
python -m venv .venv
# Activate .venv using your operating system's usual command.
python -m pip install .
rtlpub check examples/persian.xhtml
rtlpub check examples/persian.xhtml --format json
rtlpub check ./samples --format json
rtlpub check book.epub --fail-on warning
~~~

The examples are synthetic and licensed with the project. Generate an EPUB:

~~~sh
python examples/make_epub.py /tmp/rtlpub-example.epub
rtlpub check /tmp/rtlpub-example.epub --format json
~~~

On Windows, use a writable temporary path such as $env:TEMP/rtlpub-example.epub.
The checker never writes to the input. The example generator is a separate,
explicitly invoked command that creates a new synthetic file and refuses overwrite.

## What it checks

- Arabic yeh/kaf in Persian-language text, suspicious ZWNJ boundaries,
  explicit bidi controls, embedded BOMs and non-NFC text. These are advisory:
  deliberate editorial choices can be valid.
- Inherited XHTML lang/xml:lang and direction declarations. Explicit LTR
  spans, dir=auto, bdi, Arabic quotations and empty decorative alt are
  allowed. It does not infer direction from CSS.
- Missing alt, heading-level jumps, duplicate IDs and invalid dir values.
- Substantial Persian text under effective LTR direction produces an advisory
  to review author intent; short mixed snippets are not flagged. bdi defaults to auto.
- EPUB 3 required title/language/identifier metadata, manifest resources,
  spine references, navigation declaration and internal XHTML links/fragments.
  External URLs are never fetched.

Plain text defaults to Persian. Use --text-language ar for Arabic or und to
disable language-specific letter hints. XHTML declarations take precedence.
XML locations are element paths; text locations use one-based line and code-point
column numbers. Reports contain rule explanations, relative paths and locations,
never input text excerpts. File/member names can themselves contain private
information; review a report before sharing it.

## CI and exit codes

~~~sh
rtlpub check book.epub --format json --fail-on warning
~~~

Default threshold is error. --fail-on warning also stops on warnings;
--fail-on info stops on any finding. Exit 0 means no finding reached the
chosen threshold; 1 means findings reached it; 2 means invalid, unsupported,
unreadable or incompletely checked input. Warnings can still appear with exit 0.
JSON uses schema 1.0, deterministic ordering, counts and an explicit status.
See [the CLI contract](docs/CLI.md) and [rules](docs/RULES.md).

## Boundaries and input safety

EPUB 2, encrypted ZIPs, DRM and font-obfuscated EPUBs are unsupported. Ordinary
HTML without XHTML namespaces is unsupported. This version does not check full
navigation semantics, CSS/SVG references, all media types, language-tag syntax
or alternative fallback chains; internal fragment checking is limited to XHTML.
It does not change letters, digits, vowels, Arabic quotes, IDs or anchors.

Fixed budgets bound reads: 1,000 entries, 4 MiB per expanded member/text/XML file,
32 MiB compressed EPUB, 64 MiB accumulated raw and expanded data, ZIP ratio 100:1,
XML depth 128, 100,000 XML elements and 10,000 findings. All archive members,
including binary assets, consume the budget. Symlinks/junctions, unsafe ZIP paths,
duplicate members, DTDs and XML entity declarations are rejected. ZIPs are read
in memory and never extracted. See [security scope](SECURITY.md).

## Development

~~~sh
python -m pip install -e .
python -m unittest discover -v
ruff check src tests examples
ruff format --check src tests examples
pyright
python -m build
~~~

CI pins validator versions and Actions commit SHAs; it uses hosted runners,
read-only permissions and no secrets or paid AI calls. Installation/build tools
are development dependencies, not runtime components.

Read [contributing](CONTRIBUTING.md), [roadmap](ROADMAP.md), and
[planned Codex maintenance](docs/CODEX_MAINTENANCE.md).
Maintainer: [Ali Mohamadpour](https://github.com/qaribi).
License: [MIT](LICENSE). [فارسی](README.fa.md)

## Reading infrastructure / زیرساخت مطالعه / بنية القراءة / مطالعے کی بنیاد

**English.** Books and reading tools should work well for Persian, Arabic, Dari, Pashto and Urdu communities. Reusable open components can help other developers build these tools. rtlpub is our released offline preflight component for Persian text, XHTML and unencrypted EPUB 3; its present checks are documented above. [DANI Reader Web 0.1.0](https://github.com/qaribi/dani-reader-web/releases/tag/v0.1.0) is now released, with a local EPUB library, reusable reading UI/state adapter and original RTL fixtures. The independent Android EPUB/PDF edition remains in development. Reproducible examples, bug reports and contributions are welcome. [Current project status](https://github.com/qaribi).

<div dir="rtl" lang="fa">

**فارسی.** کتاب‌ها و ابزارهای مطالعه باید برای جامعه‌های فارسی، عربی، دری، پشتو و اردو به‌خوبی کار کنند. اجزای متن‌بازِ قابل بازاستفاده می‌توانند ساخت این ابزارها را برای توسعه‌دهندگان آسان‌تر کنند. rtlpub بخش منتشرشدهٔ بررسی آفلاین متن فارسی، XHTML و EPUB 3 بدون رمزگذاری است؛ آزمون‌های فعلی آن در بالا مستند شده‌اند. [DANI Reader Web ۰٫۱٫۰](https://github.com/qaribi/dani-reader-web/releases/tag/v0.1.0) با کتابخانهٔ EPUB محلی، رابط مطالعه و ذخیرهٔ وضعیت قابل بازاستفاده و نمونه‌های آزمایشی با متن تألیفی منتشر شده است. نسخهٔ مستقل Android برای EPUB/PDF هنوز در حال توسعه است. از نمونه‌های قابل بازتولید، گزارش خطا و مشارکت استقبال می‌کنیم. [وضعیت پروژه‌ها](https://github.com/qaribi).

</div>

<div dir="rtl" lang="ar">

**العربية.** ينبغي أن تعمل الكتب وأدوات القراءة جيداً لقرّاء الفارسية والعربية والدرية والبشتوية والأردية. ويمكن للمكوّنات المفتوحة القابلة لإعادة الاستخدام أن تسهّل بناء هذه الأدوات على المطوّرين. rtlpub هو مكوّننا المنشور للفحص المسبق دون اتصال بالشبكة للنص الفارسي وXHTML وEPUB 3 غير المشفّر؛ فحوصه الحالية موثّقة أعلاه. صدر [DANI Reader Web 0.1.0](https://github.com/qaribi/dani-reader-web/releases/tag/v0.1.0) بمكتبة EPUB محلية وواجهة قراءة ومحوّل حالة قابلين لإعادة الاستخدام ونصوص اختبار RTL أصلية. إصدار أندرويد المستقل لقراءة EPUB/PDF ما زال قيد التطوير. نرحّب بالأمثلة القابلة للتكرار وتقارير الأخطاء والمساهمات. [حالة المشاريع](https://github.com/qaribi).

</div>

<div dir="rtl" lang="ur">

**اردو۔** کتابوں اور مطالعے کے اوزار کو فارسی، عربی، دری، پشتو اور اردو کے قارئین کے لیے اچھی طرح کام کرنا چاہیے۔ دوبارہ استعمال کے قابل اوپن سورس اجزا، ڈویلپرز کے لیے یہ اوزار بنانا آسان کر سکتے ہیں۔ rtlpub فارسی متن، XHTML اور غیر مرموز EPUB 3 کی آف لائن ابتدائی جانچ کا ہمارا جاری شدہ جزو ہے؛ اس کی موجودہ جانچ اوپر درج ہے۔ [DANI Reader Web 0.1.0](https://github.com/qaribi/dani-reader-web/releases/tag/v0.1.0) جاری ہو چکا ہے، جس میں مقامی EPUB لائبریری، دوبارہ استعمال کے قابل ریڈنگ انٹرفیس اور اسٹیٹ اڈاپٹر، اور خود لکھے گئے RTL آزمائشی متن شامل ہیں۔ مستقل Android EPUB/PDF ایڈیشن ابھی زیرِ تعمیر ہے۔ قابلِ تکرار مثالیں، خرابیوں کی رپورٹیں اور شراکتیں خوش آئند ہیں۔ [منصوبوں کی موجودہ حالت](https://github.com/qaribi)۔

</div>
