" Mask dotenv values while leaving variable names and separators visible.
syntax match envMaskedValue /./ contained containedin=envValue conceal cchar=*

setlocal conceallevel=2
setlocal concealcursor=nc
