// §11: 2.000 píxeles en el lado mayor y calidad 0,75. Los PDF vuelven sin
// tocar (recomprimir una radiografía arriesga dejarla ilegible).
// El navegador comprime pero no valida: rechazar es del servidor.
const LADO_MAYOR = 2000
const CALIDAD = 0.75
const TIPO_SALIDA = 'image/jpeg'

function aBlob(ancho, alto, bitmap) {
  if (typeof OffscreenCanvas !== 'undefined') {
    const lienzo = new OffscreenCanvas(ancho, alto)
    dibujar(lienzo, ancho, alto, bitmap)
    return lienzo.convertToBlob({ type: TIPO_SALIDA, quality: CALIDAD })
  }
  const lienzo = document.createElement('canvas')
  lienzo.width = ancho
  lienzo.height = alto
  dibujar(lienzo, ancho, alto, bitmap)
  return new Promise((resolver, rechazar) => {
    lienzo.toBlob(
      blob => (blob ? resolver(blob) : rechazar(new Error('toBlob sin resultado'))),
      TIPO_SALIDA,
      CALIDAD,
    )
  })
}

function dibujar(lienzo, ancho, alto, bitmap) {
  const ctx = lienzo.getContext('2d')
  // JPEG no tiene transparencia: sin fondo, un PNG transparente queda negro.
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, ancho, alto)
  ctx.drawImage(bitmap, 0, 0, ancho, alto)
}

export async function comprimirEnElNavegador(file) {
  if (!file.type.startsWith('image/')) return file
  try {
    const bitmap = await createImageBitmap(file)
    const escala = Math.min(1, LADO_MAYOR / Math.max(bitmap.width, bitmap.height))
    const ancho = Math.round(bitmap.width * escala)
    const alto = Math.round(bitmap.height * escala)
    const blob = await aBlob(ancho, alto, bitmap)
    if (bitmap.close) bitmap.close()
    const nombre = file.name.replace(/\.[^.]+$/, '') + '.jpg'
    return new File([blob], nombre, { type: TIPO_SALIDA })
  } catch {
    // Si el navegador no puede leerla, no se rechaza: se manda tal cual y
    // decide el servidor.
    return file
  }
}
