import React, { useState } from "react";
import VisionEdge from "../utils/VisionEdge";
import CheckInVisitor from "../component/CheckInVisitor";
import CheckInPage from "../component/CheckInPage";

const Dashboard = () => {
  const [isVisitor, setIsVisitor] = useState(true);

  const handleToggle = () => {
    setIsVisitor((prevState) => !prevState);
  };

  return (
    <div className="font-poppins">
      <VisionEdge />

      {/* Toggle Slider */}
      <div className="flex justify-center items-center mt-4">
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            className="sr-only peer"
            type="checkbox"
            checked={!isVisitor}
            onChange={handleToggle}
          />
          {/* Slider */}
          <div className="peer relative rounded-full outline-none duration-100 after:duration-500 w-44 h-2 sm:w-54 sm:h-2 bg-blue-100 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-500 after:content-['Visitor'] after:absolute after:rounded-full after:h-6 after:w-22 sm:after:h-8 sm:after:w-28 after:bg-gradient-to-b after:from-gray-300 after:via-gray-100 after:to-gray-300 after:shadow-md after:top-1/2 after:-translate-y-1/2 after:left-1 after:flex after:justify-center after:items-center after:text-indigo-800 after:font-bold peer-checked:after:translate-x-20 sm:peer-checked:after:translate-x-24 peer-checked:after:content-['Employee'] mt-3">
          </div>
        </label>
      </div>

      <div className="flex justify-center items-center">
        {isVisitor ? <CheckInVisitor /> : <CheckInPage />}
      </div>

    </div>
  );
};

export default Dashboard;

