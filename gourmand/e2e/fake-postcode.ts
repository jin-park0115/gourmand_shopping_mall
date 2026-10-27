import type { Page } from "@playwright/test";

const POSTCODE_SCRIPT = "https://t1.kakaocdn.net/mapjsapi/bundle/postcode/prod/postcode.v2.js"; // components/AddressSearch.tsx 와 같게

// 카카오 우편번호 스크립트 대신 넣는 가짜. 실제 서비스 상태(CI · 회사망 차단)에 테스트가 흔들리지 않게 해요.
// 창 안에 '역삼동 테헤란로 152' 버튼 하나를 그리고, 누르면 진짜처럼 oncomplete 를 불러요
const FAKE = `
window.daum = { Postcode: function (o) {
  this.embed = function (el) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = "테헤란로 152 선택";
    b.onclick = function () {
      o.oncomplete({ zonecode: "06236", userSelectedType: "R", roadAddress: "서울 강남구 테헤란로 152",
        jibunAddress: "서울 강남구 역삼동 737", bname: "역삼동", buildingName: "강남파이낸스센터", apartment: "N" });
    };
    el.appendChild(b);
  };
} };`;

export async function fakePostcode(page: Page) {
  await page.route(POSTCODE_SCRIPT, (route) => route.fulfill({ contentType: "application/javascript", body: FAKE }));
}
