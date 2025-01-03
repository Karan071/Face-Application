import React, { useState, useRef } from "react";
import Webcam from "react-webcam";
import axios from "axios";
import VisionEdge from "../utils/VisionEdge";

const RegisterVisitor = () => {
  const [formData, setFormData] = useState({
    name: "",
    age: "",
    gender: "",
    contact: "",
    purposeOfVisit: "",
    description: "",
  });
  const [capturedPhoto, setCapturedPhoto] = useState(null);
  const webcamRef = useRef(null);

  const capturePhoto = () => {
    const photoSrc = webcamRef.current.getScreenshot();
    setCapturedPhoto(photoSrc);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };        

  const validateForm = () => {
    const errors = {};
    if (!formData.name) errors.name = "Name is required";
    if (!formData.age) errors.age = "Age is required";
    if (!formData.gender) errors.gender = "Gender is required";
    if (!formData.contact) {
      errors.contact = "Contact Number is required.";
    } else if (!/^\d{10}$/.test(formData.contact)) {
      errors.contact = "Contact Number must be 10 digits.";
    }
    if (!formData.purposeOfVisit) errors.purposeOfVisit = "Purpose of Visit is required";
    return errors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      alert(Object.values(errors).join("\n"));
      return;
    }

    if (!capturedPhoto) {
      alert("Please capture a photo before submitting.");
      return;
    }

    try {
      const photoBlob = await fetch(capturedPhoto).then((res) => res.blob());
      const formDataObj = new FormData();
      formDataObj.append("name", formData.name);
      formDataObj.append("age", formData.age);
      formDataObj.append("gender", formData.gender);
      formDataObj.append("contact", formData.contact);
      formDataObj.append("purposeOfVisit", formData.purposeOfVisit);
      formDataObj.append("description", formData.description);
      formDataObj.append("photo", photoBlob, "photo.jpg");

      const response = await axios.post(
        `http://localhost:8000/register-visitor/`,
        formDataObj,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      alert(response.data.message || "Visitor registered successfully!");
      setFormData({
        name: "",
        age: "",
        gender: "",
        contact: "",
        purposeOfVisit: "",
        description: "",
      });
      setCapturedPhoto(null);
    } catch (error) {
      console.error("Error while submitting the form:", error);
      alert(
        error.response?.data?.message ||
          "An error occurred while submitting the form."
      );
    }
  };

  return (
    <>
      <VisionEdge />
      <div className="font-poppins bg-gray-50 min-h-screen flex justify-center items-center px-4 sm:px-6 lg:px-8">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-center text-gradient bg-gradient-to-r from-indigo-600 via-blue-500 to-indigo-400 bg-clip-text text-transparent mb-4">
            VisionEdge <span className="font-thin text-gray-500">Visitor Check-In</span>
          </h1>
          <p className="text-center text-gray-600 mb-6">
            Register your details and capture your photo for check-in.
          </p>

          <div className="flex justify-center mb-6">
            {!capturedPhoto ? (
              <Webcam
                audio={false}
                ref={webcamRef}
                screenshotFormat="image/jpeg"
                className="border-2 rounded-lg w-full sm:w-[320px] sm:h-[240px] object-cover"
              />
            ) : (
              <img
                src={capturedPhoto}
                alt="Captured"
                className="w-50 h-60 rounded-lg object-cover border-2 border-gray-300 shadow-md"
              />
            )}
          </div>

          <form className="space-y-6">
            <div className="flex flex-col sm:flex-row gap-4">
              <input
                type="text"
                name="name"
                placeholder="Name"
                value={formData.name}
                onChange={handleChange}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring focus:ring-blue-300"
              />
              <input
                type="number"
                name="age"
                placeholder="Age"
                value={formData.age}
                onChange={handleChange}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring focus:ring-blue-300"
              />
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <input
                type="text"
                name="gender"
                placeholder="Gender"
                value={formData.gender}
                onChange={handleChange}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring focus:ring-blue-300"
              />
              <input
                type="text"
                name="contact"
                placeholder="Contact Number"
                value={formData.contact}
                onChange={handleChange}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring focus:ring-blue-300"
              />
            </div>

            <select
              name="purposeOfVisit"
              value={formData.purposeOfVisit}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring focus:ring-blue-300"
            >
              <option value="">Purpose of Visit</option>
              <option value="Meeting">Meeting</option>
              <option value="Delivery">Delivery</option>
              <option value="Interview">Interview</option>
              <option value="Others">Others</option>
            </select>

            <textarea
              name="description"
              placeholder="Description"
              value={formData.description}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring focus:ring-blue-300"
            />

            <div className="flex justify-center">
            {!capturedPhoto ? (
                <button
                  onClick={capturePhoto}
                  type="button"
                  className="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-full text-sm px-5 py-3 md:px-6 md:py-3.5 mt-2 md:mt-0"
                >
                  Capture Photo
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleSubmit}
                  className="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-full text-sm px-5 py-3 md:px-6 md:py-3.5 mt-2 md:mt-0"
                >
                  Submit
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </>
  );
};

export default RegisterVisitor;

