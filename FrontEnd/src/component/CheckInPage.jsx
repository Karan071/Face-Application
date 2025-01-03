import React, { useRef, useState } from "react";
import Webcam from "react-webcam";
import { Link } from "react-router-dom";
import axios from "axios";


const CheckInPage = () => {
  const webcamRef = useRef(null); //video ref
  const [capturedImage, setCapturedImage] = useState(null); // capture state

  const capturePhoto = () => {
    const imageSrc = webcamRef.current.getScreenshot();
    setCapturedImage(imageSrc);
  }

  //backend integrations
  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!capturedImage) { 
      alert("Please capture the photo for recognization") 
      return;
    }

    try {
      //photo base64 to blob
      const photoBlob = await fetch(capturedImage).then((res) => res.blob());
      const formData = new FormData()
      formData.append("photo", photoBlob, 'photo.jpg');

      // Handle response
      const response = await axios.post("http://localhost:8000/recognize-employee/",formData, {
        headers : {
          "Content-Type" : "multipart/form-data",
        },
      });
      const { status, name, similarity, message } = response.data;

      if (status === "success") {
        alert(
          `Recognition successful! Name: ${name}, Similarity: ${similarity.toFixed(2)}`
        );
      } else {
        alert(
          `Recognition failed. ${message || "Please try again with a clearer photo."}`
        );
      }
    } catch (error) {
      console.error("Error during the submission :", error);
      alert(
        "An error occured. Please try again!"
      )
    }
  };

  return (
    <div>
      <div className="flex flex-col items-center">
        <div className="text-center">
          <p className="text-4xl font-semibold text-gray-700 font-poppins mt-8 bg-gradient-to-r from-indigo-600 via-blue-500 to-indigo-400 inline-block text-transparent bg-clip-text">
            VisionEdge{" "}
            <span className="font-thin text-gray-700">Employee Check-In System</span>
          </p>
        </div>

        {/* Webcam Section */}
        <div className="relative w-full max-w-screen-lg flex flex-col justify-center items-center bg-white shadow-md rounded-lg p-4 mt-4">
          {!capturedImage ? (
            <Webcam
              audio={false}
              ref={webcamRef}
              screenshotFormat="image/jpeg"
              height={400}
              width={750}
              className="rounded-lg shadow-md"
            />
          ) : (
            <img
              src={capturedImage}
              alt="Captured image"
              className="rounded-lg shadow-md"
              height={400}
              width={750}
            />
          )}

          <div className="mt-6 text-center">
            <Link to="/register-employee">
              <p className="text-sm sm:text-lg text-indigo-700">
                New Employee here? Click here!
              </p>
            </Link>
          </div>

          {/* Capture Button */}
          {!capturedImage ? ( <button
              onClick={capturePhoto}
              type="button"
              className="mt-3 text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-full text-sm px-6 py-3 transition-all duration-200 ease-in-out"
            >
              Capture Photo
            </button>
          ) : (
            <button
              type="sumit"
              onClick={handleSubmit}
              className="mt-3 text-white bg-green-700 hover:bg-green-800 focus:ring-4 focus:ring-green-300 font-medium rounded-full text-sm px-6 py-3 transition-all duration-200 ease-in-out"
            >
              Submit
            </button>
          )}

        </div>
      </div>
    </div>
  );
};

export default CheckInPage;
