import React from "react";
import VisionEdge from "../utils/VisionEdge";
// import { AiOutlineCloseCircle } from "react-icons/ai";
import error from "../assets/error.png"
import { Link } from "react-router-dom";

const CheckIn = () => {
  return (
    <div className="h-screen flex flex-col bg-gray-50 font-poppins">
      <div className="w-full">
        <VisionEdge />
      </div>

      <div className="flex-1 flex flex-col items-center mt-11">
        <p className="text-5xl font-thin text-gray-700 mb-4 mt-11">
          Something Went Wrong
        </p>
        <div className="mt-9">

          <div className="flex flex-col items-center justify-center p-8 border-2 border-red-600 bg-red-50 rounded-lg shadow-lg w-96 ">

            {/* heading */}
            <h2 className="text-3xl font-bold text-gray-800 mt-4">Failed!</h2>
            {/* img */}
            <img src={error} alt="Employee Image" />

            {/* name and data passed */}
            <p className="text-gray-700 text-center text-2xl mt-3">Try Again, Something went Wrong !!</p>
            <Link>
              <button
                // onClick={onRetry}
                className="mt-6 px-5 py-2 border-2 border-red-600 text-red-600 font-semibold rounded-lg hover:bg-red-600 hover:text-white transition duration-300 ease-in-out transform hover:scale-105"
              >
                TRY AGAIN
              </button>
            </Link>


          </div>
        </div>
      </div>
    </div>
  );
};

export default CheckIn;
