/* Functional fontconfig shim (test-only) that loads the fonts listed in
 * $SMARTSCAN_FC_FONTS (one path per line), following the real fontconfig
 * string layout closely enough for Qt. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>

#define MAXF 256
typedef struct { int dummy; } FcConfig;
typedef struct { int dummy; } FcCharSet;
typedef struct { int dummy; } FcLangSet;

typedef struct FcPattern_ {
    char *family, *style, *file, *lang, *foundry, *fullname;
    int weight, slant, index, scalable, fontversion, antialias;
    double size, pixelsize;
    FcCharSet cs;
} FcPattern;

typedef struct { char *objs[16]; int n; } FcObjectSet;
typedef struct { FcPattern **fonts; int nfont, sfont; } FcFontSet;
typedef int FcBool;
typedef unsigned char FcChar8;
typedef unsigned int FcChar32;

static FcFontSet g_set = { NULL, 0, 0 };
static FcFontSet g_list = { NULL, 0, 0 };
static int g_loaded = 0, g_next_file = 0;
static const char *g_paths[MAXF];
static int g_npaths = 0;
static FcConfig g_cfg;

static FcPattern *make_pattern(const char *path) {
    const char *base = strrchr(path, '/');
    base = base ? base + 1 : path;
    char stem[256];
    snprintf(stem, sizeof(stem), "%s", base);
    char *dot = strrchr(stem, '.');
    if (dot) *dot = 0;
    char *dash = strchr(stem, '-');
    char style[128] = "Regular";
    if (dash) { snprintf(style, sizeof(style), "%s", dash + 1); *dash = 0; }
    FcPattern *p = calloc(1, sizeof(FcPattern));
    p->family = strdup(stem);
    p->style = strdup(style);
    p->file = strdup(path);
    p->lang = strdup("en");
    p->foundry = strdup("unknown");
    p->fullname = strdup(stem);
    p->weight = (strstr(style, "Bold") || strstr(style, "Black")) ? 200 : 80;
    p->slant = (strstr(style, "Italic") || strstr(style, "Oblique")) ? 100 : 0;
    p->index = 0;
    p->scalable = 1;
    p->antialias = 1;
    p->size = 12.0;
    p->pixelsize = 12.0;
    p->fontversion = 0;
    return p;
}

static void add_pattern(FcPattern *p, FcFontSet *set) {
    set->fonts = realloc(set->fonts, sizeof(FcPattern*) * (set->nfont + 1));
    set->fonts[set->nfont++] = p;
    set->sfont = set->nfont;
}

static void load_env_fonts(void) {
    if (g_loaded) return;
    g_loaded = 1;
    const char *env = getenv("SMARTSCAN_FC_FONTS");
    if (!env || !*env) return;
    char *copy = strdup(env);
    char *save = NULL;
    for (char *tok = strtok_r(copy, ":", &save); tok; tok = strtok_r(NULL, ":", &save)) {
        if (g_npaths >= MAXF) break;
        g_paths[g_npaths++] = strdup(tok);
        FcPattern *p = make_pattern(tok);
        add_pattern(p, &g_set);
    }
    free(copy);
}

static int fam_match(const char *want, const char *have) {
    if (!want || !*want) return 1;
    char a[256], b[256]; size_t i = 0;
    for (const char *s = want; *s && i < 255; s++) if (isalnum((unsigned char)*s)) a[i++] = (char)tolower((unsigned char)*s);
    a[i] = 0; i = 0;
    for (const char *s = have; *s && i < 255; s++) if (isalnum((unsigned char)*s)) b[i++] = (char)tolower((unsigned char)*s);
    b[i] = 0;
    return strstr(b, a) != NULL || strstr(a, b) != NULL;
}
static int score(const FcPattern *req, const FcPattern *f) {
    int s = 0;
    if (req->family && f->family) s += fam_match(req->family, f->family) ? 100 : 0;
    if (req->weight == f->weight) s += 20;
    if (req->slant == f->slant) s += 10;
    return s;
}

FcBool FcInit(void) { load_env_fonts(); return 1; }
FcConfig *FcConfigGetCurrent(void) { load_env_fonts(); return &g_cfg; }
FcBool FcConfigAppFontAddFile(FcConfig *c, const FcChar8 *f) {
    (void)c;
    if (!f) return 0;
    FcPattern *p = make_pattern((const char*)f);
    add_pattern(p, &g_set);
    return 1;
}
void FcConfigAppFontClear(FcConfig *c) { (void)c; }
void FcConfigDestroy(FcConfig *c) { (void)c; }
FcBool FcConfigSubstitute(FcConfig *c, FcPattern *p, int k) { (void)c;(void)p;(void)k; return 1; }
void FcDefaultSubstitute(FcPattern *p) { (void)p; }

FcPattern *FcPatternCreate(void) { FcPattern *p = calloc(1, sizeof(FcPattern)); p->weight = 80; p->scalable = 1; return p; }
void FcPatternDestroy(FcPattern *p) {
    if (!p) return;
    free(p->family); free(p->style); free(p->file); free(p->lang);
    free(p->foundry); free(p->fullname); free(p);
}
FcBool FcPatternAdd(FcPattern *p, const char *o, void *v, FcBool a) { (void)a; if (!p || !v) return 0;
    if (!strcmp(o, "family")) { free(p->family); p->family = strdup((char*)v); }
    else if (!strcmp(o, "style")) { free(p->style); p->style = strdup((char*)v); }
    else if (!strcmp(o, "weight")) p->weight = *(int*)v;
    else if (!strcmp(o, "slant")) p->slant = *(int*)v;
    else if (!strcmp(o, "file")) { free(p->file); p->file = strdup((char*)v); }
    else if (!strcmp(o, "lang")) { free(p->lang); p->lang = strdup((char*)v); }
    else if (!strcmp(o, "index")) p->index = *(int*)v;
    return 1; }
FcBool FcPatternAddString(FcPattern *p, const char *o, const FcChar8 *v) { return FcPatternAdd(p, o, (void*)v, 1); }
FcBool FcPatternAddInteger(FcPattern *p, const char *o, int v) { return FcPatternAdd(p, o, &v, 1); }
FcBool FcPatternAddDouble(FcPattern *p, const char *o, double v) { (void)p;(void)o;(void)v; return 1; }
FcBool FcPatternAddBool(FcPattern *p, const char *o, FcBool v) { (void)p;(void)o;(void)v; return 1; }
FcBool FcPatternAddWeak(FcPattern *p, const char *o, void *v, FcBool b) { return FcPatternAdd(p, o, v, b); }
FcBool FcPatternAddLangSet(FcPattern *p, const char *o, const FcLangSet *v) { (void)p;(void)o;(void)v; return 1; }
FcBool FcPatternAddCharSet(FcPattern *p, const char *o, const FcCharSet *v) { (void)p;(void)o;(void)v; return 1; }
FcBool FcPatternDel(FcPattern *p, const char *o) { (void)p;(void)o; return 1; }

FcBool FcPatternGetString(const FcPattern *p, const char *o, int i, FcChar8 **v) {
    if (!p || i != 0) return 0;
    if (!strcmp(o, "family")) { *v = (FcChar8*)p->family; return p->family != NULL; }
    if (!strcmp(o, "style")) { *v = (FcChar8*)p->style; return p->style != NULL; }
    if (!strcmp(o, "file")) { *v = (FcChar8*)p->file; return p->file != NULL; }
    if (!strcmp(o, "lang")) { *v = (FcChar8*)(p->lang ? p->lang : "en"); return 1; }
    if (!strcmp(o, "foundry")) { *v = (FcChar8*)(p->foundry ? p->foundry : "unknown"); return 1; }
    if (!strcmp(o, "fullname")) { *v = (FcChar8*)(p->fullname ? p->fullname : (p->family ? p->family : "Sans")); return 1; }
    return 0;
}
FcBool FcPatternGetInteger(const FcPattern *p, const char *o, int i, int *v) {
    if (!p || i != 0) return 0;
    if (!strcmp(o, "weight")) { *v = p->weight; return 1; }
    if (!strcmp(o, "slant")) { *v = p->slant; return 1; }
    if (!strcmp(o, "index")) { *v = p->index; return 1; }
    if (!strcmp(o, "fontversion")) { *v = p->fontversion; return 1; }
    if (!strcmp(o, "scalable")) { *v = 1; return 1; }
    return 0;
}
FcBool FcPatternGetDouble(const FcPattern *p, const char *o, int i, double *v) {
    if (!p || i != 0) return 0;
    if (!strcmp(o, "size")) { *v = p->size; return 1; }
    if (!strcmp(o, "pixelsize")) { *v = p->pixelsize; return 1; }
    return 0;
}
FcBool FcPatternGetBool(const FcPattern *p, const char *o, int i, FcBool *v) {
    if (!p || i != 0) return 0;
    if (!strcmp(o, "scalable") || !strcmp(o, "outline") || !strcmp(o, "antialias") || !strcmp(o, "hinting") || !strcmp(o, "autohint")) { *v = 1; return 1; }
    if (!strcmp(o, "color") || !strcmp(o, "embolden") || !strcmp(o, "vertical_layout")) { *v = 0; return 1; }
    return 0;
}
FcBool FcPatternGetCharSet(const FcPattern *p, const char *o, int i, FcCharSet **v) {
    (void)o; if (!p || i != 0) return 0; *v = (FcCharSet*)&p->cs; return 1;
}
FcBool FcPatternGetLangSet(const FcPattern *p, const char *o, int i, FcLangSet **v) { (void)p;(void)o;(void)i;(void)v; return 0; }

FcObjectSet *FcObjectSetCreate(void) { return calloc(1, sizeof(FcObjectSet)); }
FcBool FcObjectSetAdd(FcObjectSet *s, const char *o) { if (s && s->n < 16) s->objs[s->n++] = strdup(o); return 1; }
void FcObjectSetDestroy(FcObjectSet *s) { if (!s) return; for (int i = 0; i < s->n; i++) free(s->objs[i]); free(s); }

FcFontSet *FcFontList(FcConfig *c, FcPattern *p, FcObjectSet *o) {
    (void)c; (void)o;
    load_env_fonts();
    for (int i = 0; i < g_list.nfont; i++) FcPatternDestroy(g_list.fonts[i]);
    g_list.nfont = 0;
    for (int i = 0; i < g_set.nfont; i++)
        if (!p || !p->family || fam_match(p->family, g_set.fonts[i]->family))
            add_pattern(g_set.fonts[i], &g_list);
    return &g_list;
}
FcFontSet *FcFontSort(FcConfig *c, FcPattern *p, FcBool t, FcCharSet **s, int *r) {
    (void)c; (void)t; (void)s;
    load_env_fonts();
    FcFontSet *out = calloc(1, sizeof(FcFontSet));
    out->fonts = malloc(sizeof(FcPattern*) * (g_set.nfont ? g_set.nfont : 1));
    memcpy(out->fonts, g_set.fonts, sizeof(FcPattern*) * g_set.nfont);
    out->nfont = out->sfont = g_set.nfont;
    for (int i = 0; i < out->nfont; i++)
        for (int j = i + 1; j < out->nfont; j++)
            if (score(p, out->fonts[j]) > score(p, out->fonts[i])) {
                FcPattern *tmp = out->fonts[i]; out->fonts[i] = out->fonts[j]; out->fonts[j] = tmp;
            }
    if (r) *r = 0;
    return out;
}
FcPattern *FcFontMatch(FcConfig *c, FcPattern *p, int *r) {
    (void)c; FcPattern *best = NULL; int bs = -1;
    load_env_fonts();
    for (int i = 0; i < g_set.nfont; i++) { int s = score(p, g_set.fonts[i]); if (s > bs) { bs = s; best = g_set.fonts[i]; } }
    if (r) *r = best ? 0 : 1;
    return best;
}
FcPattern *FcFontRenderPrepare(FcConfig *c, FcPattern *pat, FcPattern *font) {
    (void)c; (void)pat;
    if (!font) return NULL;
    FcPattern *p = FcPatternCreate();
    FcPatternAddString(p, "family", (FcChar8*)font->family);
    FcPatternAddString(p, "style", (FcChar8*)font->style);
    FcPatternAddString(p, "file", (FcChar8*)font->file);
    p->weight = font->weight; p->slant = font->slant;
    return p;
}
FcBool FcFontSetAdd(FcFontSet *s, FcPattern *p) { (void)s; (void)p; return 1; }
void FcFontSetDestroy(FcFontSet *s) { (void)s; }
FcPattern *FcFreeTypeQuery(const FcChar8 *f, unsigned int i, FcCharSet *c, int *n) { (void)f;(void)i;(void)c;(void)n; return 0; }
FcPattern *FcFreeTypeQueryFace(const void *f, const FcChar8 *p, unsigned int i, FcCharSet *c) { (void)f;(void)p;(void)i;(void)c; return 0; }
FcCharSet *FcConfigGetBlanks(FcConfig *c) { (void)c; return 0; }
void *FcConfigGetFonts(FcConfig *c, int s) { (void)c;(void)s; return 0; }
FcLangSet *FcLangSetCreate(void) { return 0; }
void FcLangSetDestroy(FcLangSet *s) { (void)s; }
FcBool FcLangSetAdd(FcLangSet *s, const FcChar8 *l) { (void)s;(void)l; return 1; }
FcChar32 FcLangSetHasLang(const FcLangSet *s, const FcChar8 *l) { (void)s;(void)l; return 0; }
FcBool FcCharSetHasChar(const FcCharSet *s, FcChar32 c) { (void)s;(void)c; return 1; }
