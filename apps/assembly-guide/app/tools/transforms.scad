// Echo the RackStack transforms used by the Soyspray assembly (mini profile).
// Run with OPENSCADPATH pointing at a RackStack checkout (see regenerate-data.sh).
include <rack/assembly/common.scad>
include <rack-mount/common.scad>
profileName = "mini";

function m(x) = x;
echo(str("VAR yBarWidth=", yBarWidth));
echo(str("VAR yBarDepth=", yBarDepth));
echo(str("VAR yBarHeight=", yBarHeight));
echo(str("VAR railTotalHeight=", railTotalHeight));
echo(str("VAR xBarX=", xBarX));
echo(str("VAR xBarY=", xBarY));
echo(str("VAR xBarSideThickness=", xBarSideThickness));
echo(str("VAR rackTotalWidth=", rackTotalWidth));
echo(str("VAR rackTotalDepth=", rackTotalDepth));
echo(str("VAR stackConnectorDx=", stackConnectorDx));
echo(str("VAR stackConnectorDy=", stackConnectorDy));
echo(str("VAR connectorBottomToScrew=", connectorBottomToScrew));
echo(str("VAR mainRailSlideHexOnYBarDx=", mainRailSlideHexOnYBarDx));
echo(str("VAR mainRailSlideHexOnYBarDy=", mainRailSlideHexOnYBarDy));
echo(str("VAR xyPlateConnDx=", xyPlateConnDx));
echo(str("VAR xyPlateConnDy=", xyPlateConnDy));
echo(str("VAR basePlateConnPosX=", basePlateConnPosX));
echo(str("VAR basePlateConnPosY=", basePlateConnPosY));
echo(str("VAR rackMountScrewWidth=", rackMountScrewWidth));
echo(str("VAR railScrewHoleToOuterEdge=", railScrewHoleToOuterEdge));
echo(str("VAR railFrontThickness=", railFrontThickness));
echo(str("VAR railFootThickness=", railFootThickness));
echo(str("VAR screwDiff=", screwDiff));
echo(str("VAR numRailScrews=", numRailScrews));
echo(str("VAR uDiff=", uDiff));
echo(str("VAR rackMountScrewZDist=", rackMountScrewZDist));
echo(str("VAR feetProtrusionAngle=", feetProtrusionAngle));
echo(str("VAR stackConnectorDualSpacing=", stackConnectorDualSpacing));
echo(str("VAR fixedSideModules=", fixedSideModules));

mainRailPrintOrientation = [
    [cos(-90),  0, sin(-90), railTotalHeight],
    [0,         1, 0,        0              ],
    [-sin(-90), 0, cos(-90), 0              ],
    [0,         0, 0,        1              ]
  ];
xyPlateToYBarTrans = translate(v=[6,6,0]) * yBarBasePlateConnectorTrans;
xBarYBarScrewTrans16 = translate(v=[27,xBarSideThickness,8]) * rotate(a=[270,0,0]);
mR = xBarSpaceToYBarSpace * xBarMirrorOtherCornerTrans * yBarSpaceToXBarSpace;
railScrewLocal = translate(v = [mainRailSlideHexOnYBarDx, mainRailSlideHexOnYBarDy, -5]) * rotate(a = [-45, 0, 0]) * translate(v = [0, 0, 14]);
feetScrewLocal = translate(v=[-9,0,connectorBottomToScrew]) * rotate(a=[0,-90,0]);
mirrorOtherFeetStackConnectorTrans = translate(v=[stackConnectorDx,0,0]) * mirror(v=[1,0,0]);

echo(str("MAT xBarSpaceToYBarSpace=", xBarSpaceToYBarSpace));
echo(str("MAT yBarSpaceToXBarSpace=", yBarSpaceToXBarSpace));
echo(str("MAT mR=", mR));
echo(str("MAT yBarMirrorOtherCornerTrans=", yBarMirrorOtherCornerTrans));
echo(str("MAT xBarMirrorOtherCornerTrans=", xBarMirrorOtherCornerTrans));
echo(str("MAT yBarMainRailConnectorTrans=", yBarMainRailConnectorTrans));
echo(str("MAT upperXYTrayTrans=", upperXYTrayTrans));
echo(str("MAT secondStackTrans=", secondStackTrans));
echo(str("MAT feetToYBarTrans0=", feetToYBarTrans(0)));
echo(str("MAT stackConnectorTrans0=", stackConnectorTrans(0)));
echo(str("MAT yBarStackConnectorTrans=", yBarStackConnectorTrans));
echo(str("MAT xyPlateToYBarTrans=", xyPlateToYBarTrans));
echo(str("MAT mainRailPrintOrientation=", mainRailPrintOrientation));
echo(str("MAT feetPrint=", rotate(a=[90-feetProtrusionAngle,0,0])));
echo(str("MAT xBarYBarScrewTrans=", xBarYBarScrewTrans16));
echo(str("MAT railScrewLocal=", railScrewLocal));
echo(str("MAT feetScrewLocal=", feetScrewLocal));
echo(str("MAT mirrorOtherFeetStackConnectorTrans=", mirrorOtherFeetStackConnectorTrans));
echo(str("MAT yBarToMagnetModuleTrans=", yBarToMagnetModuleTrans));
cube(1);
