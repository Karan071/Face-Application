import React, { useState } from "react";
import bg from "../assets/adminPanel.png";
import axios from "axios";

const RegisterPage = () => {
    const [formData, setFormData] = useState({
        fullname: "",
        username: "",
        email: "",
        password: "",
        role: "",
    });

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData({ ...formData, [name]: value });
    };

    const validateForm = () => {
        const errors = {};
        if (!formData.fullName) errors.fullName = "Full name is required";
        if (!formData.username) errors.username = "Username is required";
        if (!formData.email) errors.email = "Email is required";
        if (!formData.password) errors.password = "Password is required";
        if (!formData.role) errors.role = "Role is required";
        return errors;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const errors = validateForm();
        if (Object.keys(errors).length > 0) {
            alert(Object.values(errors).join("\n"));
            return;
        }

        try {
            // TEST LINES : )
            console.log("Payload:", formData);

            const formDataObj = new URLSearchParams();
            urlEncodedData.append("fullname", formData.fullname);
            urlEncodedData.append("username", formData.username);
            urlEncodedData.append("email", formData.email);
            urlEncodedData.append("password", formData.password);
            urlEncodedData.append("role", formData.role);

            const response = await axios.post("http://localhost:8000/register/", formDataObj, {
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            });
            alert(response.data.message || "User registered successfully!");
            setFormData({
                fullname: "",
                username: "",
                email: "",
                password: "",
                role: "",
            });
        } catch (error) {
            console.error("Error while submitting the form:", error);
            alert(
                error.response?.data?.message ||
                "An error occurred while submitting the form."
            );
        }
    };

    return (
        <div
            className="h-screen w-screen bg-cover bg-center flex flex-col md:flex-row"
            style={{ backgroundImage: `url(${bg})` }}
        >
            <div className="h-full w-full md:w-1/3 flex items-center justify-center md:justify-start bg-white rounded-sm">
                <form className="max-w-lg w-full p-6 sm:p-8 bg-white rounded-md md:ml-12 mx-4">
                    {/* Title */}
                    <div className="mb-6">
                        <h3 className="text-4xl font-normal text-center md:text-left mt-4">
                            Create an Account
                        </h3>
                    </div>

                    {/* Full Name */}
                    <div className="mb-6">
                        <label className="text-black text-[15px] mb-2 block font-thin">
                            Full Name
                        </label>
                        <input
                            type="text"
                            name="fullName"
                            placeholder="Full Name"
                            value={formData.fullName}
                            onChange={handleChange}
                            className="w-full text-sm text-gray-800 bg-gray-100 px-4 py-3.5 rounded-full outline-blue-600 focus:bg-transparent"
                        />
                    </div>

                    {/* Username */}
                    <div className="mb-4">
                        <label className="text-black text-[15px] mb-2 block font-thin">
                            User Name
                        </label>
                        <input
                            name="username"
                            type="text"
                            value={formData.username}
                            onChange={handleChange}
                            required
                            className="w-full text-sm text-gray-800 bg-gray-100 px-4 py-3.5 rounded-full outline-blue-600 focus:bg-transparent"
                            placeholder="Create a user name"
                        />
                    </div>

                    {/* Email Address */}
                    <div className="mb-4">
                        <label className="text-black text-[15px] mb-2 block font-thin">
                            Email Address
                        </label>
                        <input
                            name="email"
                            type="email"
                            value={formData.email}
                            onChange={handleChange}
                            required
                            className="w-full text-sm text-gray-800 bg-gray-100 px-4 py-3.5 rounded-full outline-blue-600 focus:bg-transparent"
                            placeholder="Enter your email"
                        />
                    </div>

                    {/* Password */}
                    <div className="mb-4">
                        <label className="text-black text-[15px] mb-2 block font-thin">
                            Password
                        </label>
                        <input
                            name="password"
                            type="password"
                            value={formData.password}
                            onChange={handleChange}
                            required
                            className="w-full text-sm text-gray-800 bg-gray-100 px-4 py-3.5 rounded-full outline-blue-600 focus:bg-transparent"
                            placeholder="Enter your password"
                        />
                    </div>

                    {/* Role */}
                    <div className="mb-6">
                        <label className="text-black text-[15px] mb-2 block font-thin">
                            Role
                        </label>
                        <select
                            name="role"
                            value={formData.role}
                            onChange={handleChange}
                            className="w-full text-sm text-gray-800 bg-gray-100 px-4 py-3.5 rounded-full outline-blue-600 focus:bg-transparent"
                        >
                            <option value="">Select a Role</option>
                            <option value="user">User</option>
                            <option value="admin">Admin</option>
                        </select>
                    </div>

                    {/* Register Button */}
                    <div className="mt-6">
                        <button
                            type="button"
                            onClick={handleSubmit}
                            className="w-full py-3 text-sm tracking-wide font-semibold rounded-full text-white bg-blue-600 hover:bg-blue-700 shadow-lg"
                        >
                            Register
                        </button>
                    </div>

                    {/* Login Link */}
                    <p className="text-sm mt-8 text-gray-800 font-thin text-center">
                        Already have an account?{" "}
                        <a
                            href="/login"
                            className="text-blue-600 font-semibold hover:underline"
                        >
                            Log in here
                        </a>
                    </p>
                </form>
            </div>
        </div>
    );
};

export default RegisterPage;
