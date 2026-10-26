import { products } from '../data/products';

const errors: string[] = [];

// 상품 개수 (발제 기준 6개 이상)
if (products.length < 6) errors.push(`상품이 ${products.length}개입니다. 6개 이상 필요합니다.`);

// id 중복
const ids = products.map((p) => p.id);
const duplicated = ids.filter((id, i) => ids.indexOf(id) !== i);
if (duplicated.length) errors.push(`중복된 id: ${[...new Set(duplicated)].join(', ')}`);

products.forEach((p) => {
  const tag = `[id ${p.id} ${p.name}]`;

  if (!Number.isInteger(p.id) || p.id <= 0) errors.push(`${tag} id는 1 이상의 정수여야 합니다.`);
  if (p.price <= 0) errors.push(`${tag} 가격이 0 이하입니다.`);
  if (p.discountPrice != null && p.discountPrice >= p.price)
    errors.push(`${tag} 할인가가 정가보다 크거나 같습니다.`);
  if (p.rating < 0 || p.rating > 5) errors.push(`${tag} 평점이 0~5 범위를 벗어났습니다.`);
  if (p.reviewCount < 0 || p.stock < 0) errors.push(`${tag} 리뷰수나 재고가 음수입니다.`);
  if (p.isSoldOut !== (p.stock === 0))
    errors.push(`${tag} 재고(${p.stock})와 품절 여부(${p.isSoldOut})가 맞지 않습니다.`);
  if (!p.country.trim() || !p.category.trim()) errors.push(`${tag} 국가나 카테고리가 비어 있습니다.`);
  if (!p.imageUrl.startsWith('/') && !p.imageUrl.startsWith('https://'))
    errors.push(`${tag} 이미지 경로는 '/' 또는 'https://'로 시작해야 합니다.`);
});

// 국가·카테고리 표기 확인용 목록 (비슷한 이름이 섞여 있는지 눈으로 확인)
const countries = [...new Set(products.map((p) => p.country))];
const categories = [...new Set(products.map((p) => p.category))];
console.log(`국가 ${countries.length}개: ${countries.join(', ')}`);
console.log(`카테고리 ${categories.length}개: ${categories.join(', ')}\n`);

if (errors.length) {
  console.log(`❌ ${errors.length}개의 문제를 찾았습니다.`);
  errors.forEach((e) => console.log(' - ' + e));
  process.exit(1);
} else {
  console.log(`✅ 상품 ${products.length}개 모두 정상입니다.`);
}