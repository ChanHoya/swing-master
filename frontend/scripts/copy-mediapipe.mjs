// MediaPipe WASM 런타임을 public/ 으로 복사한다.
//
// 저장소에 커밋하지 않는 이유는 파일 하나가 11MB 이고 합쳐서 22MB 이기
// 때문이다. npm 패키지에 이미 있으므로 빌드할 때 옮기면 된다.
//
// 구글 CDN 을 런타임 의존으로 두지 않는 이유는 따로 있다. 모델과 런타임이
// 우리 도메인에서 오면 버전이 고정되고, 서버가 쓰던 것과 같은 모델이라야
// 지표 숫자가 비교 가능하다.
import { cp, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const from = join(here, "..", "node_modules", "@mediapipe", "tasks-vision", "wasm");
const to = join(here, "..", "public", "mp-wasm");

// FilesetResolver 가 SIMD 지원 여부에 따라 둘 중 하나를 고른다.
const NEEDED = [
  "vision_wasm_internal.js",
  "vision_wasm_internal.wasm",
  "vision_wasm_nosimd_internal.js",
  "vision_wasm_nosimd_internal.wasm",
];

await mkdir(to, { recursive: true });
for (const name of NEEDED) {
  await cp(join(from, name), join(to, name));
}
console.log(`mediapipe wasm ${NEEDED.length}개 복사 → public/mp-wasm`);
