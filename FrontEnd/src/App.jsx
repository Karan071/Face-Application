import Dashboard from "./pages/Dashboard";
import LandingPage from "./pages/LandingPage";
import SuccessPage from "../src/component/SuccessPage";
import ErrorPage from "../src/component/ErrorPage";
import CheckInPage from "./component/CheckInPage";
import CheckInVisitor from "./component/CheckInVisitor";
import { Routes, Route} from "react-router-dom"
import RegisterEmployee from "./pages/RegisterEmployee";
import RegisterVisitor from "./pages/RegisterVisitor";
import MainPage from "./pages/MainPage";
import PageNotFound from "./pages/PageNotFound";
import InternalServer from "./pages/InternalServer";
import RegisterPage from "./component/RegisterPage"

import Signup from "./component/Signup";

function App() {
  return (
    <>
        <Routes>
        <Route path="/" element= {<LandingPage />}/>  
        <Route path="/main-page" element = {<MainPage/>} />
        <Route path="/dashboard" element = {<Dashboard/>}/>
        <Route path="/check-visitor" element = {<CheckInVisitor/>} />
        <Route path="/check-employee" element = {<CheckInPage/>} /> 
        <Route path="/register-employee" element = {<RegisterEmployee/>} />
        <Route path="/register-visitor" element = {<RegisterVisitor/>} />
        <Route path="/success" element = {<SuccessPage/>} />
        <Route path="/error" element = {<ErrorPage/>} />

        <Route path="/login" element = {<Signup/>} />
        <Route path="/register" element = {<RegisterPage/>} />

        {/* Page not found && Internal Server error */}
        <Route path="*" element = {<PageNotFound/>} />
        <Route path="/500" element = {<InternalServer/>} />

      </Routes>     
    </>
  );
}
export default App;
