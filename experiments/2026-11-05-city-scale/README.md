# City references and canonical vehicle scale

User requested city-driving screenshots from multiple angles (MidnightClub/NeedForSpeed examples), real/game car dimensions and canonical size metadata, then proportionate cars relative to each other and Racer's world. This extends the active car-import goal; no goal replacement.

Bounds: <=300s command, <=256MiB generated output; initial selected reference images <=4MiB each/32MiB combined; >=20GiB free. Keep source URLs/hash/dimensions/actual image classifications, source-game and manufacturer size values separately, explicit trim/year distinctions and perspective limits. Screenshots can establish visual context, not absolute metric dimensions without matched camera/plane evidence. No visible browser or desktop capture; all Racer checks hidden.

Inputs: Firecrawl primary Acura2004NSX specifications, NissanHeritageZ33VersionST2002 platform reference, published MidnightClubLA andNFSHeat screenshot galleries. NSX actualimport SourceGT4wheelbase2.530m; selected350ZGT4source2.650m. Manufacturerwidthusuallyexcludesmirrors; meshboundsinclude visiblemirrors, so do not rescale geometry toforce equality. Canonical record must carry authority, units, variant/applicability and normalized collision/render bounds separately.

## Current evidence and review

Retained19referenceimages total:12publishedMCLAframes,5officialNFSHeatSteamframes,
2realLAtrafficphotos. See output/reference-manifest.json forURLs,dimensions,SHA,
credits/licenses and per-image review captions; output/gallery.html combines
references and16currenteligible-playernativecaptures. Both originalcontact sheets,
selected-reference-contact-sheet.png and individualhighresolutionframes were
reviewed. NFSHeat1 is actualHUDchase-road/intersection context;0 includespeople;
MCLA3/6/11 supplyfront/side/reartraffic/curb/intersection views. Motorcycle/scenic
frames areexplicitlynotcar-scale anchors. No screenshots usedasabsolutemetricrulers.

Canonicalassets/catalog/dimensions.json carries4factoryrecords(NSXexactyear,
Z33platformreference,Ford1973brochureOCR,GMZ06column) plusattributedsourcehashes.
assets/catalog/prepared-sizes.json carriesin-scope measuredpreparedgeometry and
roles. GT1/Redlineexcluded; MCLAambient retainedtraffic-only, neverplayereligible.
Authoredlimits2%wheelbase/tracks and3%length/groundheight. Bodyspanheight differs
fromgroundheight, visiblewidth differsfromfactorymirror conventions; no widthfit.

output/native-seven-v1 is a retainedfailedfixture run (scenevalidator omittednew
scale mode);v2 passesloaderbutcareerpostsobscuredviews;v3 removespostsandusesfixed
camera. Historicalv3 has28views includingthen-unexcludedresearchpilots; do notuse
it as currentplayerrosteracceptance. Currentoutput/eligible-four-v1 has16views,
allactualassetSHA/bodywheelcontainment andnativeGPUloads pass. Exactmanifestbuild
andmodelsarepreserved. REAcontrolledcaptureev_a02b7592b995d3ebb2803c8184b4c9b2c9051f097ebd5669d2f7841a31f2b97d
observesv3batchprocess exit0; firstsystemPythonprobe lackedPillow andisretained
separately. This isRacerrendering,notdonorgameexecution.

Freshreview: MC3unscaledsourcebody wasincomplete;exactnative7partrepairrestores
bodylength4.6796instead4.3695. ExperimentaluniformGMwheelbasecalibrationfactor
0.946477makesWB2.6543,length4.4291,height1.2216,buttracks1.3885vsGM1.585/1.590;
thereforefailsnewtrackchecksandremainsineligible. Decisionjudgmentpredatedtrack
check; itdoesnotjustifyoverridingnewmeasurement. Originalsourceandbothprepared
versionsretained. SLRRstaticrestfit likewiseunresolved. Fourcurrentplayercars
(NSX,GT4Z,Mustang,Juiced2Z)passcanonicalcomparisonswithvariant/materiallimits.

Verification:39CTesttargets pass in car-models/output/ctest-acceptance.log; five
scalechecks include misleadingmatchingWB/wrongtrack rejection; calibrationfixture
checksunchangedBIN+oneuniformroot+allpivot/radius/width scaling. Strongindependent
reviewconfirmedprimaryNSX/Nissansourcevalues andFordnodecapfix; nativefunctional
andvisualchecksprovideadditionalbounded evidence.

Nextaction: completeMCLAplayer350Znativeassembly/wheels, SLRRrestfit andMC3track
space; updatecanonicalrecords onlywithattributedproof. No wholecityimplemented:
worldremainsflat1kmgridwith4×3mlanes/100mblocks. Allnativechecks hidden, local
reference images and snapshots retained; unknownscope neverpromotedtosupported.

## Current seven-player scale review — 2026-11-06

Explicituserexclusionsnowapplylisting/acquisition/publication; raw1435recordcatalogretained, active965includes41deferredtraffic. RealMCLAplayerRoadsterhas2006Nissanowner-manualdimensionsandpress-kittyreradii; primarymanualPDFpixelsunavailable403, fulltexttablewithvariant/roundinglimits retained. MC3source-trackconflictresolvedforRacerbydeclaredfactoryWB+wheelmountadaptation; originalsretained. SLRRfixedauthoredposehasindependenttrianglesteeringclearance/nativeimages, nonativeequilibriumclaim. Sevenplayerinventoryupdatedwithscopeinassets/catalog/prepared-sizes.json; oneambientrecordremainstraffic-only.

Nextboundedcapture: `python3 scripts/verify_vehicle_scale.py experiments/2026-11-05-city-scale/output/eligible-seven-v3 --limit 7`,28hidden1280×720views,≤240sbatch/15sprocess,≤128MiBadditionaloutputandtotal≤256MiBleaf,≥20GiBfree. Thiswillfreezeexactcurrent7preparations/executableandhistories, includingmetadata-correctedSLRRv4. Currentfive-v2andolderfour-v1 remainhistoricalandgallerywillmarkthembyscope. Rootwillreviewall28carviews; publishedreferenceimagesarenotmetricproof.

The current seven-player batch completed:28views,98.21s, all native hash/containment/load checks pass on exact executable7a42fc7c…. Root inspected all seven four-angle detail sheets and retained fullPNG originals. The rebuilt localgallery verifies19reference+28currentmetric+21maximum-steer imagehashes. Olderfour-playergalleryHTML ispreserved asoutput/gallery-four-original.html. Currentmanifest andexactmodels liveinoutput/eligible-seven-v3; factorydimensionagreement andnativeparity remainseparate.
