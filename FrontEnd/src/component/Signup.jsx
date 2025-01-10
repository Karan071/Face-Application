import React, {useState} from "react";
import bg from "../assets/adminPanel.png";
import axios from "axios";

const LoginPage = () => {
    const [formData, setFormData] = useState({
        username: "",
        password: "",
    });

    const validateForm = () => {
        const errors = {};
        if (!formData.email) errors.email = "Email is required";
        if (!formData.password) errors.password = "Password is required";
        return errors;
    }

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData({ ...formData, [name]: value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const errors = validateForm();
        if (Object.keys(errors).length > 0) {
            alert(Object.values(errors).join("\n"));
            return;
        }
    
        try {
            // Prepare data in URL-encoded format
            const urlEncodedData = new URLSearchParams();
            urlEncodedData.append("username", formData.username);
            urlEncodedData.append("password", formData.password);
            // const formDataObj = new FormData();
            // formDataObj.append("username", formData.username);
            // formDataObj.append("password", formData.password);
    
            const response = await axios.post("http://localhost:8000/token/", urlEncodedData, {
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    // "Content-Type": "multipart/form-data",
                    
                },
            });
    
            alert(response.data.access_token || "Login successful!");
            setFormData({
                email: "",
                password: "",
            });
        } catch (error) {
            console.error("Error while submitting the form:", error);
            console.error("Error response data:", error.response?.data);
            alert(
                error.response?.data?.detail ||
                "An error occurred while submitting the form."
            );
        }
    };
    

    return (
        <div
            className="h-screen w-screen bg-cover bg-center flex flex-col md:flex-row "
            style={{ backgroundImage: `url(${bg})` }}
        >
            {/* Form Container */}
            <div className="h-full w-full md:w-1/3 flex items-center justify-center md:justify-start bg-white rounded-sm font-mono">
                <form className="max-w-lg w-full p-6 sm:p-8 bg-white rounded-md md:ml-12 mx-4">
                    <div className="mb-6">

                        <h3 className="text-4xl font-normal text-center md:text-left mt-4">
                            Login 
                        </h3>

                    </div>

                    {/* Email Input */}
                    <div>
                        <label className="text-black text-[15px] mb-2 block font-thin">
                            Username
                        </label>
                        <div className="relative">
                            <input
                                name="email"
                                value={formData.email}
                                onChange={handleChange}
                                type="text"
                                required
                                className="w-full text-sm text-gray-800 bg-gray-100 px-4 py-3.5 rounded-full outline-blue-600 focus:bg-transparent"
                                placeholder="Enter your username"
                            />
                        </div>
                    </div>

                    {/* Password Input */}
                    <div className="mt-6">
                        <label className="text-black text-[15px] mb-2 block font-thin">
                            Password
                        </label>
                        <div className="relative">
                            <input
                                name="password"
                                value={formData.password}   
                                onChange={handleChange}
                                type="password"
                                required
                                className="rounded-full w-full text-sm text-gray-800 bg-gray-100 px-4 py-3.5 outline-blue-600 focus:bg-transparent"
                                placeholder="Enter your password"
                            />
                        </div>
                    </div>

                    {/* Login Button */}
                    <div className="mt-8">
                        <button
                            type="button"
                            onClick={handleSubmit}
                            className="w-full py-3 text-sm tracking-wide font-semibold rounded-full text-white bg-blue-600 hover:bg-blue-700 shadow-lg"
                        >
                            Log in
                        </button>
                    </div>

                    {/* Registration Link */}
                    <p className="text-sm mt-8 text-gray-800 font-thin text-center">
                        Don't have an account?{" "}

                        <a
                            href="/register"
                            className="text-blue-600 font-semibold hover:underline"
                        >
                            Register here
                        </a>

                    </p>
                </form>
            </div>
        </div>
    );
};

export default LoginPage;

// import React, { useState } from "react";
// import bg from "../assets/adminPanel.png";
// import axios from "axios";

// const Signup = () => {
//     const [formData, setFormData] = useState({
//         email: "",
//         password: "",
//     });

//     const validateForm = () => {
//         const errors = {};
//         if (!formData.email) errors.email = "Email is required";
//         if (!formData.password) errors.password = "Password is required";
//         return errors;
//     };

//     const handleChange = (e) => {
//         const { name, value } = e.target;
//         setFormData({ ...formData, [name]: value });
//     };

//     const handleSubmit = async (e) => {
//         e.preventDefault();
//         const errors = validateForm();
//         if (Object.keys(errors).length > 0) {
//             alert(Object.values(errors).join("\n"));
//             return;
//         }

//         try {
//             const formDataObj = new FormData();
//             formDataObj.append("email", formData.email);
//             formDataObj.append("password", formData.password);

//             const response = await axios.post("http://localhost:8000/token/", formDataObj, {
//                 headers: {
//                     "Content-Type": "multipart/form-data",
//                 },
//             });

//             alert(response.data.message || "User logged in successfully!");
//             setFormData({
//                 email: "",
//                 password: "",
//             });
//         } catch (error) {
//             console.error("Error while submitting the form:", error);
//             alert(
//                 error.response?.data?.message ||
//                 "An error occurred while submitting the form."
//             );
//         }
//     };
    

//     return (
//         <div
//             className="h-screen w-screen bg-cover bg-center flex flex-col md:flex-row"
//             style={{ backgroundImage: `url(${bg})` }}
//         >
//             <div className="h-full w-full md:w-1/3 flex items-center justify-center md:justify-start bg-white rounded-sm">
//                 <form
//                     className="max-w-lg w-full p-6 sm:p-8 bg-white rounded-md md:ml-12 mx-4"
//                     // onSubmit={handleSubmit} 
//                 >
//                     <h3 className="text-4xl font-normal text-center md:text-left mt-4">Login</h3>

//                     <div className="mt-6">
//                         <label className="text-black text-[15px] mb-2 block font-thin">
//                             Email Address
//                         </label>
//                         <input
//                             name="email"
//                             value={formData.email}
//                             onChange={handleChange}
//                             type="email"
//                             required
//                             className="w-full text-sm text-gray-800 bg-gray-100 px-4 py-3.5 rounded-full outline-blue-600 focus:bg-transparent"
//                             placeholder="Enter your email"
//                         />
//                     </div>

//                     <div className="mt-6">
//                         <label className="text-black text-[15px] mb-2 block font-thin">
//                             Password
//                         </label>
//                         <input
//                             name="password"
//                             value={formData.password}
//                             onChange={handleChange}
//                             type="password"
//                             required
//                             className="rounded-full w-full text-sm text-gray-800 bg-gray-100 px-4 py-3.5 outline-blue-600 focus:bg-transparent"
//                             placeholder="Enter your password"
//                         />
//                     </div>

//                     <button
//                         type="button" 
//                         onChange={handleSubmit}
//                         className="w-full py-3 text-sm tracking-wide font-semibold rounded-full text-white bg-blue-600 hover:bg-blue-700 shadow-lg mt-8"
//                     >
//                         Log in
//                     </button>

//                     <p className="text-sm mt-8 text-gray-800 font-thin text-center">
//                         Don't have an account?{" "}
//                         <a
//                             href="/register"
//                             className="text-blue-600 font-semibold hover:underline"
//                         >
//                             Register here
//                         </a>
//                     </p>
//                 </form>
//             </div>
//         </div>
//     );
// };

// export default Signup;
