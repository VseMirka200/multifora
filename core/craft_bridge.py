"""Run official Craft Windows CLI binaries, without opening editor windows."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ENGINES = ('pdfcraft','wordcraft','deckcraft','gridcraft','photocraft','vectorcraft')
class CraftError(RuntimeError): pass

class CraftBridge:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))/'engines'

    def exe_path(self, engine):
        if engine not in ENGINES: raise CraftError(f'Неизвестный движок: {engine}')
        base = self.root/engine
        files = sorted(base.rglob(f'{engine}-cli.exe'))
        if len(files) != 1: raise CraftError(f'{engine}: CLI не найден или неоднозначен. Запустите INSTALL_ENGINES.bat из папки Multifora.')
        return files[0].resolve()

    def available(self, engine):
        try: return self.exe_path(engine).is_file()
        except CraftError: return False

    def require(self, engine):
        self.exe_path(engine)

    def _run(self, engine, *args):
        exe = self.exe_path(engine)
        try:
            r = subprocess.run([str(exe),*map(str,args)], cwd=exe.parent, stdin=subprocess.DEVNULL, capture_output=True, encoding='utf-8',errors='replace',timeout=900,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except (OSError, subprocess.TimeoutExpired) as e: raise CraftError(f'{engine}: {e}') from e
        if r.returncode: raise CraftError(f'{engine} (код {r.returncode}): {(r.stderr or r.stdout)[-8000:]}')
        return r.stdout, r.stderr

    def call(self, engine, op, **p):
        self.require(engine)
        # Use a private staging directory: some CLI commands reject existing output files.
        if 'input' in p: p['input']=str(Path(p['input']).resolve(strict=True))
        if 'inputs' in p: p['inputs']=[str(Path(x).resolve(strict=True)) for x in p['inputs']]
        if 'output' not in p: return self._dispatch(engine,op,p)
        dest=Path(p['output']).resolve()
        with tempfile.TemporaryDirectory(prefix='.craft-',dir=dest.parent) as tmp:
            candidate=Path(tmp)/dest.name
            result=self._dispatch(engine,op,{**p,'output':str(candidate)})
            if not candidate.is_file() or candidate.stat().st_size==0: raise CraftError(f'{engine}: выходной файл не создан')
            # Never replace an actual nonempty file supplied as the destination.
            if dest.exists() and dest.stat().st_size: raise CraftError(f'Файл уже существует: {dest}')
            os.replace(candidate,dest)
            return result

    def _dispatch(self,e,op,p):
        i=p.get('input'); o=p.get('output'); ext=Path(o or '').suffix.lower()
        run=lambda *a:self._run(e,*a)
        def done(result):
            _,err=result
            return {'warnings':err.strip()} if 'warning' in err.lower() else {}
        def cmd(name, params=None): return name+'='+json.dumps(params or {},ensure_ascii=False)
        if e=='wordcraft':
            if op=='convert': return done(run('convert',i,o,*(['--strict'] if ext in ('.pdf','.png') else [])))
            if op=='merge':
                paths=p['inputs']; args=['run','--file',paths[0]]
                for path in paths[1:]: args+=['--cmd',cmd('caret.docEnd'),'--cmd',cmd('insert.pageBreak'),'--cmd',cmd('insert.textFromFile',{'path':path})]
                run(*args,'--save',o)
                return {'warnings':'Проверьте колонтитулы, секции и разбивку страниц.'}
        if e=='deckcraft':
            if op=='sample': return done(run('run','--sample','--save',o))
            if op=='convert': return done(run('run','--in',i,'--save' if ext in ('.pptx','.deckcraft') else '--export',o))
            if op=='render': return done(run('render',i,'--slide',p['page'],o))
            if op=='page_count':
                with tempfile.TemporaryDirectory() as tmp:
                    run('render',i,'--all',tmp)
                    return {'pages':len(list(Path(tmp).glob('slide-*.png')))}
        if e=='gridcraft' and op=='convert': return done(run('run','--in',i,'--out',o))
        if e=='vectorcraft' and op=='convert': return done(run('--safe-mode','convert',i,o))
        if e=='photocraft' and op in ('convert','compress'):
            args=['convert',i,o]
            if 'quality' in p: args+=['--quality',str(p['quality'])]
            return done(run(*args))
        if e=='pdfcraft':
            if op=='page_count':
                data=json.loads(run('info',i)[0]); pages=data.get('pages',data.get('page_count'))
                if isinstance(pages,list): pages=len(pages)
                if type(pages) is not int or pages<1: raise CraftError('PdfCraft: неизвестный формат ответа info')
                return {'pages':pages}
            if op=='render': return done(run('render',i,'--page',p['page']+1,'--dpi',p.get('dpi',144),'--out',o))
            if op=='extract': return done(run('extract',i,'--pages',','.join(str(x+1) for x in p['pages']),'--out',o))
            if op=='merge':
                paths=p['inputs']; order=p.get('page_order') or []
                with tempfile.TemporaryDirectory() as tmp:
                    if order:
                        chunks=[]
                        for n,(s,page) in enumerate(order):
                            part=str(Path(tmp)/f'{n}.pdf'); run('extract',paths[s],'--pages',page+1,'--out',part); chunks.append(part)
                        paths=chunks
                    if len(paths)==1: shutil.copyfile(paths[0],o); return {}
                    return done(run('combine',*paths,'--out',o))
            if op=='compress':
                method=p.get('method','auto')
                if method in ('quality','optimize'): raise CraftError('Режим без потерь пока не подключён к CLI PdfCraft.')
                with tempfile.TemporaryDirectory() as tmp:
                    run('batch',i,'--steps','optimize','--out-dir',tmp,'--stop-on-error','--ppi',96 if method=='max' else 150,'--quality',45 if method=='max' else 60)
                    files=list(Path(tmp).rglob('*.pdf'))
                    if len(files)!=1: raise CraftError('PdfCraft: не найден единственный результат оптимизации')
                    shutil.copyfile(files[0],o); return {}
        raise CraftError(f'{e}: операция {op} не поддерживается')

bridge=CraftBridge()
