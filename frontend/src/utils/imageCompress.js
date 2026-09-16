/**
 * Compressão de imagens no browser via canvas.
 * Redimensiona mantendo proporção e exporta como JPEG/WEBP com qualidade configurável.
 */

const ALLOWED_TYPES = new Set(["image/jpeg", "image/jpg", "image/png", "image/webp"]);
const ALLOWED_EXTS = new Set([".jpg", ".jpeg", ".png", ".webp"]);

export function isValidImageType(file) {
  const type = (file.type || "").toLowerCase();
  if (ALLOWED_TYPES.has(type)) return true;
  // fallback por extensão quando type vem vazio (alguns Android)
  const name = (file.name || "").toLowerCase();
  for (const ext of ALLOWED_EXTS) if (name.endsWith(ext)) return true;
  return false;
}

/**
 * Comprime um File/Blob de imagem.
 * @param {File|Blob} file
 * @param {{maxWidth:number,maxHeight:number,quality:number,mime:string}} opts
 * @returns {Promise<Blob>}
 */
export async function compressImage(file, opts = {}) {
  const {
    maxWidth = 1600,
    maxHeight = 1600,
    quality = 0.82,
    mime = "image/jpeg",
  } = opts;

  // Se já é pequeno e é JPEG, pode retornar direto (evita recompressão desnecessária)
  // mas ainda validamos dimensões — imagem 4000px mesmo com 800KB deve ser reduzida
  const bitmap = await loadBitmap(file);
  let { width, height } = bitmap;

  // Calcular escala mantendo proporção
  const scale = Math.min(1, maxWidth / width, maxHeight / height);
  const outW = Math.round(width * scale);
  const outH = Math.round(height * scale);

  // Se não precisa redimensionar nem transcodificar, e já é jpeg pequeno, retorna original
  const isJpeg = (file.type || "").toLowerCase().includes("jpeg") || (file.type || "").toLowerCase().includes("jpg");
  if (scale === 1 && isJpeg && mime === "image/jpeg" && file.size < 900 * 1024) {
    if (bitmap.close) bitmap.close();
    return file;
  }

  const canvas = document.createElement("canvas");
  canvas.width = outW;
  canvas.height = outH;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    if (bitmap.close) bitmap.close();
    return file;
  }
  // Fundo branco para PNG com transparência → JPEG
  if (mime === "image/jpeg") {
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, outW, outH);
  }
  // drawImage aceita ImageBitmap
  ctx.drawImage(bitmap, 0, 0, outW, outH);
  if (bitmap.close) bitmap.close();

  const blob = await new Promise((resolve, reject) => {
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error("Falha ao comprimir imagem"))),
      mime,
      quality
    );
  });
  return blob;
}

async function loadBitmap(file) {
  // createImageBitmap é mais eficiente e respeita orientação EXIF em alguns browsers
  if (typeof createImageBitmap === "function") {
    try {
      return await createImageBitmap(file);
    } catch {
      // fallback
    }
  }
  return await loadViaImage(file);
}

function loadViaImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      // Criar um ImageBitmap-like mínimo: objeto com width/height e que drawImage aceita
      // mas canvas drawImage aceita HTMLImageElement direto, então retornamos a própria img
      // com um close no-op
      img.close = () => {};
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Imagem inválida"));
    };
    img.src = url;
  });
}

/**
 * Converte dataURL (ex. de canvas) para Blob.
 */
export function dataUrlToBlob(dataUrl) {
  const [header, base64] = dataUrl.split(",");
  const mime = header.match(/:(.*?);/)?.[1] || "image/png";
  const bin = atob(base64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return new Blob([arr], { type: mime });
}

export const COMPRESS_PRESETS = {
  selfie: { maxWidth: 1280, maxHeight: 1280, quality: 0.8, mime: "image/jpeg" },
  documento: { maxWidth: 1920, maxHeight: 1920, quality: 0.85, mime: "image/jpeg" },
};
