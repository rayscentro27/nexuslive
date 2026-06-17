export type ShowroomSocialApprovalItem = {
  id: string;
  sourceType: 'facebook_queue_item' | 'facebook_publish_proof' | 'social_approval_packet';
  title: string;
  queueItemId: string;
  captionPreview: string;
  cta: string;
  approvalStatus: 'published' | 'queued_for_review' | 'needs_review';
  platform: 'facebook';
  channel: string;
  qualityScore?: number | null;
  proofPostId?: string;
  proofPermalink?: string;
  approveCommand?: string;
  dryRunCommand?: string;
  publishCommand?: string;
};

export const showroomSocialApprovalManifest: ShowroomSocialApprovalItem[] = 
[
  {
    id: "fb-proof-social-b8d626a59169fbc8",
    sourceType: "facebook_publish_proof",
    title: "Published proof: Funding readiness before cash is needed",
    queueItemId: "social_b8d626a59169fbc8",
    captionPreview: "The worst time to get funding-ready is the day you need cash. Start with your business docs, business identity consistency, bank statements, and realistic expectations.",
    cta: "Comment READY for the Credit/Funding Readiness Checklist.",
    approvalStatus: "published",
    platform: "facebook",
    channel: "Clear Credentials",
    qualityScore: null,
    proofPostId: "131069194210954_1303567701943955",
    proofPermalink: "https://www.facebook.com/131069194210954/posts/1303567701943955"
  },
  {
    id: "fb-creative-social_d0c2b0b68bb238b5",
    sourceType: "facebook_queue_item",
    title: "Smoke Test 0% Business Credit Post 1",
    queueItemId: "social_d0c2b0b68bb238b5",
    captionPreview: "Before you chase 0% business credit, make sure your business does not look unfinished.\n\nFunding readiness starts with entity details, EIN, business phone, address, website, domain email, NAICS, bank statements, and credit-readiness gaps. Ne",
    cta: "Comment READY for the checklist.",
    approvalStatus: "queued_for_review",
    platform: "facebook",
    channel: "Clear Credentials",
    qualityScore: 99,
    approveCommand: "python3 scripts/social_queue_approve.py --item-id social_d0c2b0b68bb238b5 --ray-approved",
    dryRunCommand: "python3 scripts/social_publish_facebook_queue_item.py --item-id social_d0c2b0b68bb238b5 --dry-run",
    publishCommand: "SOCIAL_PUBLISHING_ENABLED=true SOCIAL_DRY_RUN=false python3 scripts/social_publish_facebook_queue_item.py --item-id social_d0c2b0b68bb238b5 --confirm-real-publish"
  },
  {
    id: "fb-creative-social_b831540efdc10898",
    sourceType: "facebook_queue_item",
    title: "Smoke Test 0% Business Credit Post 2",
    queueItemId: "social_b831540efdc10898",
    captionPreview: "Before you chase 0% business credit, make sure your business does not look unfinished.\n\nFunding readiness starts with entity details, EIN, business phone, address, website, domain email, NAICS, bank statements, and credit-readiness gaps. Ne",
    cta: "Comment READY for the checklist.",
    approvalStatus: "queued_for_review",
    platform: "facebook",
    channel: "Clear Credentials",
    qualityScore: 99,
    approveCommand: "python3 scripts/social_queue_approve.py --item-id social_b831540efdc10898 --ray-approved",
    dryRunCommand: "python3 scripts/social_publish_facebook_queue_item.py --item-id social_b831540efdc10898 --dry-run",
    publishCommand: "SOCIAL_PUBLISHING_ENABLED=true SOCIAL_DRY_RUN=false python3 scripts/social_publish_facebook_queue_item.py --item-id social_b831540efdc10898 --confirm-real-publish"
  },
  {
    id: "fb-creative-social_a65d2e8ff66d194c",
    sourceType: "facebook_queue_item",
    title: "Smoke Test 0% Business Credit Post 3",
    queueItemId: "social_a65d2e8ff66d194c",
    captionPreview: "Before you chase 0% business credit, make sure your business does not look unfinished.\n\nFunding readiness starts with entity details, EIN, business phone, address, website, domain email, NAICS, bank statements, and credit-readiness gaps. Ne",
    cta: "Comment READY for the checklist.",
    approvalStatus: "queued_for_review",
    platform: "facebook",
    channel: "Clear Credentials",
    qualityScore: 99,
    approveCommand: "python3 scripts/social_queue_approve.py --item-id social_a65d2e8ff66d194c --ray-approved",
    dryRunCommand: "python3 scripts/social_publish_facebook_queue_item.py --item-id social_a65d2e8ff66d194c --dry-run",
    publishCommand: "SOCIAL_PUBLISHING_ENABLED=true SOCIAL_DRY_RUN=false python3 scripts/social_publish_facebook_queue_item.py --item-id social_a65d2e8ff66d194c --confirm-real-publish"
  },
  {
    id: "fb-creative-social_4646e8352ce40e45",
    sourceType: "facebook_queue_item",
    title: "Day 2 Post 1: Story Problem",
    queueItemId: "social_4646e8352ce40e45",
    captionPreview: "A business owner gets denied and says, \u201cBut I have an LLC.\u201d\n\nThe LLC was never the whole game. Business bankability is the stack: entity, EIN, phone, address, website, domain email, business profile, bank behavior, documentation, and credit",
    cta: "Comment READY / DM READY / Start with the $97 review",
    approvalStatus: "queued_for_review",
    platform: "facebook",
    channel: "Clear Credentials",
    qualityScore: 97,
    approveCommand: "python3 scripts/social_queue_approve.py --item-id social_4646e8352ce40e45 --ray-approved",
    dryRunCommand: "python3 scripts/social_publish_facebook_queue_item.py --item-id social_4646e8352ce40e45 --dry-run",
    publishCommand: "SOCIAL_PUBLISHING_ENABLED=true SOCIAL_DRY_RUN=false python3 scripts/social_publish_facebook_queue_item.py --item-id social_4646e8352ce40e45 --confirm-real-publish"
  },
  {
    id: "fb-creative-social_05d5b6c813060764",
    sourceType: "facebook_queue_item",
    title: "Day 7 Post 1: Story Problem",
    queueItemId: "social_05d5b6c813060764",
    captionPreview: "A business owner gets denied and says, \u201cBut I have an LLC.\u201d\n\nThe LLC was never the whole game. Business bankability is the stack: entity, EIN, phone, address, website, domain email, business profile, bank behavior, documentation, and credit",
    cta: "Comment READY / DM READY / Start with the $97 review",
    approvalStatus: "queued_for_review",
    platform: "facebook",
    channel: "Clear Credentials",
    qualityScore: 97,
    approveCommand: "python3 scripts/social_queue_approve.py --item-id social_05d5b6c813060764 --ray-approved",
    dryRunCommand: "python3 scripts/social_publish_facebook_queue_item.py --item-id social_05d5b6c813060764 --dry-run",
    publishCommand: "SOCIAL_PUBLISHING_ENABLED=true SOCIAL_DRY_RUN=false python3 scripts/social_publish_facebook_queue_item.py --item-id social_05d5b6c813060764 --confirm-real-publish"
  },
  {
    id: "fb-creative-social_c1c7dba696e6e66e",
    sourceType: "facebook_queue_item",
    title: "Day 2 Post 2: Direct Offer",
    queueItemId: "social_c1c7dba696e6e66e",
    captionPreview: "Before you chase 0% business credit cards, check if your profile is ready for the conversation.\n\nTier 1 funding prep is not magic. It is consistency, documentation, credit readiness, business bankability, and timing.\n\nThe $97 Nexus Starter ",
    cta: "Comment READY / DM READY / Start with the $97 review",
    approvalStatus: "queued_for_review",
    platform: "facebook",
    channel: "Clear Credentials",
    qualityScore: 94,
    approveCommand: "python3 scripts/social_queue_approve.py --item-id social_c1c7dba696e6e66e --ray-approved",
    dryRunCommand: "python3 scripts/social_publish_facebook_queue_item.py --item-id social_c1c7dba696e6e66e --dry-run",
    publishCommand: "SOCIAL_PUBLISHING_ENABLED=true SOCIAL_DRY_RUN=false python3 scripts/social_publish_facebook_queue_item.py --item-id social_c1c7dba696e6e66e --confirm-real-publish"
  },
  {
    id: "fb-creative-social_196cc108dc3055bf",
    sourceType: "facebook_queue_item",
    title: "Day 7 Post 2: Direct Offer",
    queueItemId: "social_196cc108dc3055bf",
    captionPreview: "Before you chase 0% business credit cards, check if your profile is ready for the conversation.\n\nTier 1 funding prep is not magic. It is consistency, documentation, credit readiness, business bankability, and timing.\n\nThe $97 Nexus Starter ",
    cta: "Comment READY / DM READY / Start with the $97 review",
    approvalStatus: "queued_for_review",
    platform: "facebook",
    channel: "Clear Credentials",
    qualityScore: 94,
    approveCommand: "python3 scripts/social_queue_approve.py --item-id social_196cc108dc3055bf --ray-approved",
    dryRunCommand: "python3 scripts/social_publish_facebook_queue_item.py --item-id social_196cc108dc3055bf --dry-run",
    publishCommand: "SOCIAL_PUBLISHING_ENABLED=true SOCIAL_DRY_RUN=false python3 scripts/social_publish_facebook_queue_item.py --item-id social_196cc108dc3055bf --confirm-real-publish"
  },
  {
    id: "fb-creative-social_5c036763d9743278",
    sourceType: "facebook_queue_item",
    title: "Day 1 Post 2: Education",
    queueItemId: "social_5c036763d9743278",
    captionPreview: "Your business may look real to you and unfinished to a lender.\n\nA lender may see mismatched addresses, no business phone, thin web presence, weak bank statements, unclear NAICS, or credit-report issues that have not been organized.\n\nThat is",
    cta: "Comment READY / DM READY / Start with the $97 review",
    approvalStatus: "queued_for_review",
    platform: "facebook",
    channel: "Clear Credentials",
    qualityScore: 91,
    approveCommand: "python3 scripts/social_queue_approve.py --item-id social_5c036763d9743278 --ray-approved",
    dryRunCommand: "python3 scripts/social_publish_facebook_queue_item.py --item-id social_5c036763d9743278 --dry-run",
    publishCommand: "SOCIAL_PUBLISHING_ENABLED=true SOCIAL_DRY_RUN=false python3 scripts/social_publish_facebook_queue_item.py --item-id social_5c036763d9743278 --confirm-real-publish"
  },
  {
    id: "fb-creative-social_2e9f95c7a6754ede",
    sourceType: "facebook_queue_item",
    title: "Day 3 Post 1: Education",
    queueItemId: "social_2e9f95c7a6754ede",
    captionPreview: "Credit repair without a funding plan can still leave you stuck when the opportunity shows up.\n\nPossible inaccuracies, outdated items, unverifiable accounts, or documentation gaps should be organized into a factual dispute workflow. But lend",
    cta: "Comment READY / DM READY / Start with the $97 review",
    approvalStatus: "queued_for_review",
    platform: "facebook",
    channel: "Clear Credentials",
    qualityScore: 91,
    approveCommand: "python3 scripts/social_queue_approve.py --item-id social_2e9f95c7a6754ede --ray-approved",
    dryRunCommand: "python3 scripts/social_publish_facebook_queue_item.py --item-id social_2e9f95c7a6754ede --dry-run",
    publishCommand: "SOCIAL_PUBLISHING_ENABLED=true SOCIAL_DRY_RUN=false python3 scripts/social_publish_facebook_queue_item.py --item-id social_2e9f95c7a6754ede --confirm-real-publish"
  },
  {
    id: "fb-creative-social_420640d8a110a29f",
    sourceType: "facebook_queue_item",
    title: "Day 6 Post 2: Education",
    queueItemId: "social_420640d8a110a29f",
    captionPreview: "Your business may look real to you and unfinished to a lender.\n\nA lender may see mismatched addresses, no business phone, thin web presence, weak bank statements, unclear NAICS, or credit-report issues that have not been organized.\n\nThat is",
    cta: "Comment READY / DM READY / Start with the $97 review",
    approvalStatus: "queued_for_review",
    platform: "facebook",
    channel: "Clear Credentials",
    qualityScore: 91,
    approveCommand: "python3 scripts/social_queue_approve.py --item-id social_420640d8a110a29f --ray-approved",
    dryRunCommand: "python3 scripts/social_publish_facebook_queue_item.py --item-id social_420640d8a110a29f --dry-run",
    publishCommand: "SOCIAL_PUBLISHING_ENABLED=true SOCIAL_DRY_RUN=false python3 scripts/social_publish_facebook_queue_item.py --item-id social_420640d8a110a29f --confirm-real-publish"
  }
];
