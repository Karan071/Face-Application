import React, { useRef, useState } from "react";
import Webcam from "react-webcam";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { RxLoop } from "react-icons/rx";


const CheckInPage = () => {
  const webcamRef = useRef(null); //video ref
  const [capturedImage, setCapturedImage] = useState(null); // capture state
  const navigate = useNavigate();

  const capturePhoto = () => {
    const imageSrc = webcamRef.current.getScreenshot();
    setCapturedImage(imageSrc);
  }

  const retake = () => {
    setCapturedImage(null)
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
        navigate('/success', {
          state: {
            name,
            similarity: similarity.toFixed(2),
            photo: capturedImage
          }
        });
      } else {
        // alert(
        //   `Recognition failed. ${message || "Please try again with a clearer photo."}`
        // );
        navigate("/error")
      }
    } catch (error) {
      console.error("Error during the submission :", error);
      // alert(
      //   "An error occured. Please try again!"
      // )
      navigate("/error")
    }
  };

  return (
    <div>
      <div className="flex flex-col items-center font-mono">
        <div className="text-center">
          <p className="text-4xl font-semibold text-gray-700 mt-8 bg-gradient-to-r from-indigo-600 via-blue-500 to-indigo-400 inline-block text-transparent bg-clip-text">
            VisionEdge{" "}
            <span className="font-thin text-gray-700">Employee Check-In System</span>
          </p>
        </div>

        {/* Webcam Section */}
        <div className="relative w-full max-w-screen-lg flex flex-col justify-center items-center bg-white rounded-lg p-4 mt-4">
          {!capturedImage ? (
            <Webcam
              audio={false}
              ref={webcamRef}
              screenshotFormat="image/jpeg"
              height={400}
              width={750}
              className="rounded-lg"
            />
          ) : (
            <img
              src={capturedImage}
              alt="Captured image"
              className="rounded-lg"
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
            <div className="flex justify-center items-center gap-10">
              <button
                type="submit"
                onClick={handleSubmit}
                className="mt-3 text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-full text-sm px-6 py-3 transition-all duration-200 ease-in-out"
              >
                Submit
              </button>
              <button
                className="mt-3 text-gray-600 hover:text-blue-700 focus:outline-none transition-colors duration-200"
                onClick={() => retake()}
              >
                <RxLoop className="w-6 h-6" />
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default CheckInPage;
