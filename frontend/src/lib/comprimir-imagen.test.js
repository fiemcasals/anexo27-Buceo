// @vitest-environment jsdom
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { comprimirEnElNavegador } from './comprimir-imagen'

// jsdom no trae createImageBitmap ni OffscreenCanvas, y su <canvas> no dibuja.
// Se reemplazan por dobles que registran con qué medidas y calidad se pidió
// la imagen: eso es lo que este módulo decide.
let lienzos
let pedidos
let llamadasAlContexto

function instalarOffscreenCanvas() {
  class FalsoOffscreenCanvas {
    constructor(width, height) {
      this.width = width
      this.height = height
      lienzos.push(this)
    }
    getContext() {
      const ctx = {
        fillStyle: '',
        fillRect: (...a) => llamadasAlContexto.push(['fillRect', ctx.fillStyle, ...a]),
        drawImage: (...a) => llamadasAlContexto.push(['drawImage', ...a.slice(1)]),
      }
      return ctx
    }
    async convertToBlob(opciones) {
      pedidos.push(opciones)
      return new Blob(['jpeg'], { type: opciones.type })
    }
  }
  vi.stubGlobal('OffscreenCanvas', FalsoOffscreenCanvas)
}

function instalarBitmap(width, height) {
  vi.stubGlobal('createImageBitmap', vi.fn(async () => ({ width, height, close() {} })))
}

beforeEach(() => {
  lienzos = []
  pedidos = []
  llamadasAlContexto = []
  instalarOffscreenCanvas()
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('comprimirEnElNavegador', () => {
  it('reduce una imagen grande a 2000 px de lado mayor', async () => {
    instalarBitmap(4000, 3000)
    await comprimirEnElNavegador(new File(['x'], 'placa.png', { type: 'image/png' }))
    expect([lienzos[0].width, lienzos[0].height]).toEqual([2000, 1500])
  })

  it('reduce tambien cuando el lado mayor es el alto', async () => {
    instalarBitmap(3000, 6000)
    await comprimirEnElNavegador(new File(['x'], 'placa.png', { type: 'image/png' }))
    expect([lienzos[0].width, lienzos[0].height]).toEqual([1000, 2000])
  })

  it('no agranda una imagen que ya es mas chica que 2000 px', async () => {
    instalarBitmap(800, 600)
    await comprimirEnElNavegador(new File(['x'], 'placa.png', { type: 'image/png' }))
    expect([lienzos[0].width, lienzos[0].height]).toEqual([800, 600])
  })

  it('pide calidad 0,75 y JPEG', async () => {
    instalarBitmap(4000, 3000)
    await comprimirEnElNavegador(new File(['x'], 'placa.png', { type: 'image/png' }))
    expect(pedidos).toEqual([{ type: 'image/jpeg', quality: 0.75 }])
  })

  it('pinta un fondo blanco antes de dibujar, porque el JPEG no tiene transparencia', async () => {
    instalarBitmap(4000, 3000)
    await comprimirEnElNavegador(new File(['x'], 'placa.png', { type: 'image/png' }))
    expect(llamadasAlContexto).toEqual([
      ['fillRect', '#fff', 0, 0, 2000, 1500],
      ['drawImage', 0, 0, 2000, 1500],
    ])
  })

  it('libera el bitmap al terminar', async () => {
    const close = vi.fn()
    vi.stubGlobal('createImageBitmap', vi.fn(async () => ({ width: 4000, height: 3000, close })))
    await comprimirEnElNavegador(new File(['x'], 'placa.png', { type: 'image/png' }))
    expect(close).toHaveBeenCalledTimes(1)
  })

  it('deja un PDF intacto', async () => {
    instalarBitmap(4000, 3000)
    const pdf = new File(['%PDF-1.7'], 'ecg.pdf', { type: 'application/pdf' })
    const salida = await comprimirEnElNavegador(pdf)
    expect(salida).toBe(pdf)
    expect(lienzos).toHaveLength(0)
    expect(createImageBitmap).not.toHaveBeenCalled()
  })

  it('devuelve un File, no un Blob, para que el nombre sobreviva', async () => {
    instalarBitmap(4000, 3000)
    const salida = await comprimirEnElNavegador(
      new File(['x'], 'radiografia.png', { type: 'image/png' }))
    expect(salida).toBeInstanceOf(File)
    expect(salida.name).toBe('radiografia.jpg')
    expect(salida.type).toBe('image/jpeg')
  })

  it('usa un <canvas> comun cuando el navegador no tiene OffscreenCanvas', async () => {
    vi.stubGlobal('OffscreenCanvas', undefined)
    instalarBitmap(4000, 3000)
    const medidas = []
    const pedidoToBlob = []
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
      () => ({ drawImage() {}, fillRect() {}, fillStyle: '' }))
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation(function (cb, tipo, calidad) {
      medidas.push([this.width, this.height])
      pedidoToBlob.push([tipo, calidad])
      cb(new Blob(['jpeg'], { type: tipo }))
    })
    const salida = await comprimirEnElNavegador(
      new File(['x'], 'placa.png', { type: 'image/png' }))
    expect(medidas).toEqual([[2000, 1500]])
    expect(pedidoToBlob).toEqual([['image/jpeg', 0.75]])
    expect(salida).toBeInstanceOf(File)
  })

  it('no valida ni rechaza: si el navegador no puede leer la imagen, la devuelve tal cual', async () => {
    vi.stubGlobal('createImageBitmap', vi.fn(async () => { throw new Error('no decodifica') }))
    const rara = new File(['x'], 'foto.heic', { type: 'image/heic' })
    await expect(comprimirEnElNavegador(rara)).resolves.toBe(rara)
  })
})
