@ECHO OFF

pushd %~dp0

set SOURCEDIR=source
set BUILDDIR=build
set SPHINXBUILD=sphinx-build

if "%1" == "" goto help

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR%

:end
popd
