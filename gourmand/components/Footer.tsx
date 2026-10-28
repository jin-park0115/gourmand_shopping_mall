export default function Footer() {
  return (
    <footer data-shop-chrome className="border-t border-gray-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-4 py-8 text-center md:flex-row md:gap-6 md:text-left">
        {/* 팀 로고 */}
        <img src="/images/common/team_logo.webp" alt="크런치클럽" className="h-12 w-auto md:h-14" />

        {/* 안내 문구 */}
        <div className="text-sm text-gray-500">
          <p className="font-bold text-gray-700">구르망 GOURMAND · 세계의 과자를 한 곳에서</p>
          <p className="mt-1">상품 이미지는 학습용으로 사용되었으며, 저작권은 각 제조사에 있습니다.</p>
        </div>
      </div>
    </footer>
  );
}
