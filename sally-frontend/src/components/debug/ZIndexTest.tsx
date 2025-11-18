import React from 'react'

const ZIndexTest: React.FC = () => {
  return (
    <div className="fixed top-4 right-4 z-[100] bg-black text-white p-4 rounded-lg">
      <h3 className="font-bold mb-2">Z-Index Test</h3>
      <div className="text-sm space-y-1">
        <p>Navbar: z-50</p>
        <p>CustomerSidebar: z-40</p>
        <p>CustomerLayout: z-10</p>
        <p>This box: z-100</p>
      </div>
    </div>
  )
}

export default ZIndexTest
