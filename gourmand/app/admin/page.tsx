import AdminDashboard from "@/components/admin/AdminDashboard";

// 관리자 · 주문/배송 관리 (/admin)
// 쇼핑몰 화면에는 이동 버튼이 없고 주소로만 들어와요. 관리자 계정으로 로그인해야 보여요 (SCRUM-36)
export default function AdminPage() {
  return <AdminDashboard />;
}
