# Maintainer: Odd Østlie <oddostlie@gmail.com>
pkgname=oddwinefixes-git
_pkgname=oddwinefixes
pkgver=0.1.0
pkgrel=1
pkgdesc="A PE Analyser and Wine/Proton missing dependency/font fixer"
arch=('any')
url="https://github.com/TheOddPirate/oddwinefixes"
license=('LGPL-2.1-or-later')
depends=(
    'python'
    'python-pefile'
)
makedepends=(
    'git'
    'uv'
    'python-installer'
)
provides=("${_pkgname}")
conflicts=("${_pkgname}")
source=("git+${url}.git")
sha256sums=('SKIP')



build() {
    cd "${_pkgname}"
    uv build
}

package() {
    cd "${_pkgname}"
    python -m installer --destdir="${pkgdir}" dist/*.whl
}
